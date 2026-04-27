"""
Semantic rules for astanalyzer.

This module defines static analysis rules that target semantic issues in Python code,
i.e. patterns that may lead to incorrect behaviour, hidden bugs, or unclear intent.

Unlike style rules, which focus on formatting and readability, semantic rules aim to:
- detect logically suspicious constructs (e.g. always-true conditions, redundant assignments)
- identify error-prone patterns (e.g. mutable default arguments, bare except clauses)
- highlight misuse of language features (e.g. comparison to None using == instead of is)
- surface potential bugs that are not syntax errors but may lead to incorrect runtime behaviour

The rules are built using the AstroDSL matcher DSL and operate on `astroid` AST nodes.

Each rule:
- extends the `Rule` base class
- defines one or more matchers describing the target pattern
- optionally provides fixers (safe or advisory)
- may suggest refactorings or structural improvements

Design principles:
- prioritise correctness and clarity over aggressive auto-fixing
- avoid unsafe transformations unless they are provably semantics-preserving
- prefer advisory fixes (comments, hints) when behaviour cannot be safely inferred
- keep rules explainable and transparent to the user

Note:
Some semantic issues require deeper data-flow or control-flow analysis.
These rules intentionally operate on AST-level heuristics and therefore may:
- produce conservative warnings
- provide partial or non-automatic fixes

Future extensions may include:
- data-flow analysis
- inter-procedural reasoning
- integration with type information
"""

from __future__ import annotations

from ..enums import NodeType, RuleCategory, Severity
from ..fixer import fix
from ..matcher import match
from ..rule import Rule
from ..tools import is_builtin_print_call


class AlwaysTrueConditionIf(Rule):
    """
    WHAT:
    Detects if statements whose condition can be determined as always true.

    WHY:
    An always-true condition makes the if statement redundant because the guarded
    block will always execute. This can hide leftover debugging code, obsolete
    conditions, or a logic mistake where a real condition was intended.

    WHEN:
    This is usually relevant in normal application logic, tests, and validation
    code. It may be intentional in temporary debugging code, generated code, or
    code where a constant condition is used to keep a block visually isolated.

    HOW:
    Remove the redundant condition and keep the body if the behaviour is intended.
    If a real condition was expected, replace the constant expression with the
    correct condition before flattening the code.
    """
    id = "SEM-001"
    title = "Condition is always true"
    severity = Severity.WARNING
    category = RuleCategory.SEMANTIC
    node_type = {NodeType.IF}

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("If").where_test_reason(any=True)
        ]
        self.fixer_builders = [
            fix()
            .flatten_always_true_if()
            .because("Condition is always true; keep only the body."),
        ]


class AlwaysTrueConditionWhile(Rule):
    """
    WHAT:
    Detects while loops whose condition can be determined as always true.

    WHY:
    An always-true while condition creates a potentially infinite loop. This can
    cause non-terminating behaviour, high CPU usage, blocked execution, or code
    that relies on hidden break statements to exit.

    WHEN:
    This is important in application logic, services, scripts, and loops that do
    not clearly contain an exit path. It may be intentional in event loops,
    servers, workers, REPLs, or loops that deliberately terminate through break,
    return, exceptions, or external signals.

    HOW:
    Add an explicit exit condition when the loop should terminate normally. If the
    infinite loop is intentional, make the exit mechanism clear and document or
    suppress the advisory finding.
    """
    id = "SEM-002"
    title = "While condition is always true"
    severity = Severity.WARNING
    category = RuleCategory.SEMANTIC
    node_type = NodeType.WHILE

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("While").where_test_reason(any=True)
        ]
        self.fixer_builders = [
            fix()
            .add_review_note_and_ignore(
                "SEM-002",
                "Loop condition is always true; verify that an infinite loop is intended.",
            )
            .because(
                "Add a review note and suppress this advisory semantic finding "
                "until the loop condition is manually reviewed."
            ),
        ]


class CompareToNoneUsingEq(Rule):
    """
    WHAT:
    Detects comparisons to None using == or !=.

    WHY:
    None is a singleton in Python and should be compared by identity. Equality
    operators can be affected by custom __eq__ implementations, which may produce
    unexpected results or obscure the intended None check.

    WHEN:
    This is relevant whenever code checks whether a value is absent or uninitialised.
    It is rarely intentional to use == or != with None, except in unusual cases
    where custom equality behaviour is explicitly being tested.

    HOW:
    Replace x == None with x is None, and x != None with x is not None.
    """
    id = "SEM-003"
    title = "Comparison to None using == or !="
    severity = Severity.WARNING
    category = RuleCategory.SEMANTIC
    node_type = NodeType.COMPARE

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Compare").where_compare_pairwise(
                op_in=("Eq", "NotEq"),
                any_side_value=None,
            )
        ]
        self.fixer_builders = [
            fix()
            .replace_none_comparison_operator()
            .because("Use 'is' or 'is not' when comparing with None."),
        ]


class AssignmentInCondition(Rule):
    """
    WHAT:
    Detects assignments inside if or while conditions using the walrus operator.

    WHY:
    Assignment inside a condition combines state change with control-flow
    decision-making. Although valid Python, it can make the condition harder to
    read and increases the chance that the assigned value or branch logic is
    misunderstood.

    WHEN:
    This is most relevant in complex conditions, long expressions, or code written
    for maintainability by a wider team. It may be acceptable when the assignment
    is simple and idiomatic, such as while chunk := file.read(size): or if match
    := pattern.search(text):.

    HOW:
    Move the assignment before the condition when clarity improves. Keep the walrus
    operator only when it makes the code shorter without hiding the control-flow
    logic, and suppress the advisory finding if intentional.
    """
    id = "SEM-004"
    title = "Assignment in condition (walrus)"
    severity = Severity.WARNING
    category = RuleCategory.SEMANTIC
    node_type = {NodeType.IF, NodeType.WHILE}

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("If|While").where_contains("NamedExpr", in_="test")
        ]
        self.fixer_builders = [
            fix()
            .add_review_note_and_ignore(
                "SEM-004",
                "Assignment inside condition (':=') detected. "
                "Consider assigning before the condition for clarity.",
            )
            .because(
                "Add a review note and suppress this advisory semantic finding "
                "until the condition is manually reviewed."
            ),
        ]


class RedeclaredVariable(Rule):
    """
    WHAT:
    Detects variables that are assigned again in the same block before the previous
    assigned value is used.

    WHY:
    The earlier assignment has no observable effect if its value is overwritten
    before being read. This may indicate redundant code, a missed use of the first
    value, or an accidental overwrite caused by reusing the same variable name.

    WHEN:
    This is relevant in sequential logic, calculations, parsing, and data
    transformation code. It may be intentional when a variable is deliberately
    reinitialised for clarity, but that pattern should be obvious from context.

    HOW:
    Remove the earlier assignment if it is truly redundant. If both values are
    needed, use the first value before reassignment or rename one of the variables
    to make the intent clear.
    """
    id = "SEM-005"
    title = "Redeclared variable in the same scope"
    severity = Severity.WARNING
    category = RuleCategory.SEMANTIC
    node_type = NodeType.ASSIGN

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Assign")
            .where_target_name()
            .overwritten_without_use_in_same_block()
        ]
        self.fixer_builders = [
            fix()
            .add_review_note_and_ignore(
                "SEM-005",
                "Variable is reassigned before the previous value is used. Check whether this is intentional or a lost assignment.",
            )
            .because(
                "Add a review note and suppress this semantic finding until the reassignment is manually reviewed."
            ),
            fix()
            .remove_node(ref="previous_assign")
            .because("Remove redundant earlier assignment."),
        ]


class ExceptionNotUsed(Rule):
    """
    WHAT:
    Detects except clauses that bind the caught exception to a variable but never
    use that variable.

    WHY:
    Binding an exception name suggests that the exception object is important.
    If it is never used, the alias adds noise and may indicate missing logging,
    missing error handling, or leftover debugging code.

    WHEN:
    This is relevant when exception details should be logged, inspected, re-raised,
    or included in an error response. It may be acceptable when the alias is a
    placeholder during development, though using _ is clearer for intentionally
    unused values.

    HOW:
    Remove the unused exception alias if the exception object is not needed. If
    the details matter, use the variable for logging, diagnostics, wrapping, or
    re-raising.
    """
    id = "SEM-006"
    title = "Exception bound in except-clause is not used"
    severity = Severity.INFO
    category = RuleCategory.SEMANTIC
    node_type = NodeType.EXCEPT_HANDLER

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("ExceptHandler")
            .where_except_binds_name(ignore="_")
            .where_body_missing_name("")
        ]
        self.fixer_builders = [
            fix()
            .add_review_note_and_ignore(
                "SEM-006",
                "Exception object is bound but not used. Consider logging it, re-raising it, or removing the alias.",
            )
            .because(
                "Add a review note and suppress this advisory semantic finding until manually reviewed."
            ),
            fix()
            .remove_except_alias()
            .because("Remove unused exception binding."),
        ]


class BareExcept(Rule):
    """
    WHAT:
    Detects bare except: clauses that do not specify an exception type.

    WHY:
    A bare except catches all exceptions, including KeyboardInterrupt and
    SystemExit. This can hide programming errors, make debugging harder, and
    prevent expected shutdown or interruption behaviour.

    WHEN:
    This is relevant in almost all application code. It may be intentional only at
    very high-level crash boundaries, cleanup code, or defensive wrappers where all
    exceptions must be captured and handled carefully.

    HOW:
    Catch a specific exception type whenever possible. If a broad handler is
    needed, prefer except Exception: and ensure the exception is logged or handled
    explicitly.
    """
    id = "SEM-007"
    title = "Bare except clause"
    severity = Severity.INFO
    category = RuleCategory.SEMANTIC
    node_type = NodeType.EXCEPT_HANDLER

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("ExceptHandler").where("type", "none")
        ]
        self.fixer_builders = [
            fix()
            .replace_bare_except_with_exception()
            .because("Replace bare except with except Exception."),
            fix()
            .add_review_note_and_ignore(
                "SEM-007",
                "Bare 'except:' catches all exceptions. Consider catching a specific exception type.",
            )
            .because(
                "Add a review note and suppress this advisory semantic finding "
                "until exception handling is manually reviewed."
            ),
        ]


class MutableDefaultArgument(Rule):
    """
    WHAT:
    Detects function parameters that use mutable objects such as lists,
    dictionaries, or sets as default values.

    WHY:
    Default argument values are evaluated once when the function is defined, not
    each time it is called. A mutable default can therefore be shared across calls,
    causing state to leak between independent invocations.

    WHEN:
    This is important whenever the default object may be modified inside the
    function or passed to code that can modify it. It may be intentional only when
    shared state across calls is explicitly desired, which should be documented.

    HOW:
    Use None as the default value and create a new mutable object inside the
    function when needed, for example: if value is None: value = [].
    """
    id = "SEM-008"
    title = "Mutable default argument"
    severity = Severity.WARNING
    category = RuleCategory.SEMANTIC
    node_type = {NodeType.FUNCTION_DEF}

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("FunctionDef").where_mutable_default_argument()
        ]
        self.fixer_builders = [
            fix()
            .replace_mutable_default_with_none()
            .insert_mutable_default_guard()
            .because("Replace mutable default with None and initialise inside the function."),
        ]


class PrintDebugStatement(Rule):
    """
    WHAT:
    Detects print() calls used as standalone expression statements.

    WHY:
    Debug print statements can leave unwanted output in production code, make
    runtime output inconsistent, and bypass the project's logging configuration.
    They may also expose internal values or make automated output harder to parse.

    WHEN:
    This is relevant in application code, libraries, services, and command-line
    tools with structured output. It may be acceptable in small scripts, examples,
    teaching code, or intentional CLI output, where print() is part of the user
    interface rather than debugging.

    HOW:
    Remove temporary debug prints. For diagnostics, replace them with the logging
    module or the project's logging abstraction. Keep print() only when it is
    intentional user-facing output.
    """
    id = "SEM-009"
    title = "Print debug statement"
    severity = Severity.WARNING
    category = RuleCategory.SEMANTIC
    node_type = NodeType.EXPR

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Expr").with_child(
                match("Call").satisfies(is_builtin_print_call)
            )
        ]
        self.fixer_builders = [
            fix()
            .add_review_note_and_ignore(
                "SEM-009",
                "Debug print statement detected. Use logging instead or remove this line.",
            )
            .because(
                "Add a review note and suppress this advisory semantic finding "
                "until the debug output is manually reviewed."
            ),
            fix()
            .delete_node()
            .because("Remove debug print statement."),
        ]


__all__ = [
    "AlwaysTrueConditionIf",
    "AlwaysTrueConditionWhile",
    "CompareToNoneUsingEq",
    "AssignmentInCondition",
    "RedeclaredVariable",
    "ExceptionNotUsed",
    "BareExcept",
    "MutableDefaultArgument",
    "PrintDebugStatement",
]
