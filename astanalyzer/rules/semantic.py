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
    id = "COND-001"
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
    id = "COND-003"
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
    id = "CMP-001"
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
    id = "ASSIGN-001"
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
    id = "VAR-002"
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
    id = "EXC-015"
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
    id = "EXC-001"
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
    id = "ARG-017"
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
    id = "DBG-023"
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