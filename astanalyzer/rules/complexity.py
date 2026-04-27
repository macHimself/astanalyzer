"""
Complexity-oriented rules for astanalyzer.

This module defines static analysis rules that highlight functions or control
structures whose shape suggests growing complexity and reduced readability.

The rules focus on patterns such as:
- functions with too many parameters
- control-flow nesting that is too deep

These findings are mostly advisory. Automatic fixes are intentionally limited
to comments and guidance because safe structural refactoring usually requires
developer intent and broader semantic context.
"""

from __future__ import annotations

from ..enums import NodeType, RuleCategory, Severity
from ..fixer import fix
from ..matcher import match
from ..rule import Rule
from ..tools import arg_count_gt, function_arg_count, parent_depth_at_least, count_relevant_statements


class TooManyArguments(Rule):
    """
    Function has too many parameters.

    A large number of parameters can make a function harder to read, understand,
    and maintain. It often indicates that the function is doing too much or that
    related data could be grouped together.

    Consider reducing the number of parameters by introducing a data structure
    (e.g. a class or dataclass) or splitting the function into smaller parts.
    """
    MAX_ARGS = 5
    id = "CX-001"
    title = "Function has too many parameters"
    severity = Severity.WARNING
    category = RuleCategory.COMPLEXITY
    node_type = NodeType.FUNCTION_DEF

    def __init__(self):
        super().__init__()
        # self.matchers = [
        #     match("FunctionDef|AsyncFunctionDef")
        #     .where("__custom_condition__", arg_count_gt(self.MAX_ARGS))
        # ]
        self.matchers = [
            match("FunctionDef|AsyncFunctionDef").where(
                "__custom_condition__",
                arg_count_gt(self.MAX_ARGS, ignore_bound_first_arg=True, ignore_init=True),
            )
        ]
        self.fixer_builders = [
            fix()
            .add_review_note_and_ignore(
                "CX-001",
                lambda node: (
                    f"Function has {function_arg_count(node, ignore_bound_first_arg=True, ignore_init=True)} parameters "
                    f"(recommended <= {self.MAX_ARGS}). "
                    "Consider grouping related parameters into an object/dataclass "
                    "or splitting the function into smaller responsibilities."
                ),
            )
            .because("Add a review note and suppress this advisory complexity finding.")
        ]


class TooDeepNesting(Rule):
    """
    Code is nested too deeply.

    Deep nesting increases cognitive complexity and makes the code harder to read,
    reason about, and maintain. It often indicates that the logic could be simplified
    or reorganized.

    Consider using guard clauses, early returns/continues, or extracting nested logic
    into separate functions.
    """
    id = "CX-002"
    title = "Too deep nesting"
    MAX_DEPTH = 3
    severity = Severity.WARNING
    category = RuleCategory.COMPLEXITY
    node_type = {NodeType.IF, NodeType.FOR, NodeType.WHILE, NodeType.TRY}

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("If|For|While|Try").where(
                "__custom_condition__",
                parent_depth_at_least(
                    ("If", "For", "While", "Try"),
                    self.MAX_DEPTH,
                ),
            )
        ]
        self.fixer_builders = [
            fix()
            .add_review_note_and_ignore(
                "CX-002",
                lambda node: (
                    "Nested control flow is too deep. "
                    "Consider extracting part of the logic into a helper function, "
                    "using guard clauses, or simplifying conditional branches."
                ),
            )
            .because(
                "Add a review note and suppress this advisory complexity finding "
                "until the nested control flow is manually refactored."
            )
        ]


class FunctionTooLong(Rule):
    """
    Function is too long.

    Long functions are harder to read, understand, test, and maintain. They often
    indicate that multiple responsibilities are combined into a single unit.

    Consider breaking the function into smaller, focused helper functions.
    """
    id = "CX-003"
    title = "Too long function"
    MAX_LINES = 40
    severity = Severity.WARNING
    category = RuleCategory.COMPLEXITY
    node_type = {NodeType.FUNCTION_DEF, NodeType.ASYNC_FUNCTION_DEF}

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("FunctionDef|AsyncFunctionDef").satisfies(
                lambda node: count_relevant_statements(node) > self.MAX_LINES
                # lambda node: hasattr(node, "lineno")
                # and hasattr(node, "end_lineno")
                # and (node.end_lineno - node.lineno + 1) > self.MAX_LINES
            )
        ]
        self.fixer_builders = [
            fix()
            .add_review_note_and_ignore(
                "CX-003",
                lambda node: (
                    f"Function has {len(getattr(node, 'body', []))} top-level statements. "
                    "Consider splitting it into smaller functions with focused responsibilities."
                ),
            )
            .because(
                "Add a review note and suppress this advisory complexity finding "
                "until the function is manually refactored."
            )
        ]


__all__ = [
    "TooManyArguments",
    "TooDeepNesting",
    "FunctionTooLong",
]
