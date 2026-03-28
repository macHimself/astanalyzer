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


class AlwaysTrueConditionIf(Rule):
    """
    This condition is always true.

    An always-true condition makes the surrounding 'if' statement redundant,
    because the guarded block will always execute. This may indicate unnecessary
    control flow, a logic mistake, or leftover debugging code.

    Consider removing the condition and keeping only the body if this behavior is intentional.
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
    While loop condition is always true.

    This creates a potentially infinite loop, which may lead to high CPU usage
    or a program that never terminates unless explicitly interrupted.

    Ensure that this behavior is intentional, or consider adding a proper exit condition.
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
            .comment_before(
                "Loop condition is always true; verify that an infinite loop is intended."
            )
            .because("While loop condition is always true."),
        ]


class CompareToNoneUsingEq(Rule):
    """
    Comparison to None using '==' or '!='.

    In Python, None should be compared using 'is' or 'is not', not equality
    operators. Using '==' or '!=' can lead to incorrect behavior if an object
    overrides equality semantics.

    Consider replacing the comparison with 'is None' or 'is not None'.
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
    Assignment inside a condition using the walrus operator (':=').

    While valid in Python, assignments within conditions can reduce readability
    and make the control flow harder to understand, especially in more complex expressions.

    Consider moving the assignment outside of the condition if it improves clarity.
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
            .comment_before(
                "Assignment inside condition (':=') detected. Consider assigning before the condition for clarity."
            )
            .because("Assignment inside condition reduces readability."),
        ]


class RedeclaredVariable(Rule):
    """
    Variable is reassigned before its previous value is used.

    This may indicate redundant code, a logical error, or an unintended overwrite.
    The earlier assignment has no effect if its value is never used.

    Consider removing the unused assignment or renaming variables to clarify intent.
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
            .comment_before(
                "Redeclaration in the same block without prior use. Consider removing the earlier assignment or renaming."
            )
            .because("Variable is reassigned before the previous value is used."),
            fix()
            .remove_node(ref="previous_assign")
            .because("Remove redundant earlier assignment."),
        ]


class ExceptionNotUsed(Rule):
    """
    Exception is assigned to a variable but never used.

    Binding an exception to a name in an 'except' clause is unnecessary if the
    variable is not used. This may indicate leftover debugging code or a missed
    opportunity to log or handle the exception details.

    Consider removing the unused alias or using it meaningfully.
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
            .comment_before(
                "Exception is bound but never used. Remove the alias or log/raise the exception."
            )
            .because("Bound exception variable is unused."),
            fix()
            .remove_except_alias()
            .because("Remove unused exception binding."),
        ]


class BareExcept(Rule):
    """
    Bare 'except:' clause catches all exceptions.

    Using a bare 'except:' will catch all exceptions, including system-exiting
    ones like KeyboardInterrupt and SystemExit. This can hide bugs and make
    debugging difficult.

    Consider catching a more specific exception or using 'except Exception:' instead.
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
            .comment_before(
                "Bare 'except:' catches all exceptions. Consider a specific exception type."
            )
            .because("Bare except is too broad."),
        ]


class MutableDefaultArgument(Rule):
    """
    Function uses a mutable object as a default argument.

    Mutable default arguments (e.g. lists, dictionaries) are evaluated only once
    at function definition time, not each time the function is called. This can
    lead to unexpected behavior, as the same object is reused across calls.

    Consider using None as the default and initializing the value inside the function.
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
    Debug print statement detected.

    Using print() for debugging can leave unwanted output in production code,
    make logs inconsistent, and expose internal details during execution.

    Consider removing the statement or replacing it with proper logging.
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
                match("Call").where_call(name="print")
            )
        ]
        self.fixer_builders = [
            fix()
            .comment_before(
                "Debug print statement detected. Use logging instead or remove this line."
            )
            .because("Debug print statements should not remain in production code."),
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
