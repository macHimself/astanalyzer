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
from ..tools import arg_count_gt, function_arg_count, parent_depth_at_least


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
    id = "COMPLEX-001"
    title = "Function has too many parameters"
    severity = Severity.WARNING
    category = RuleCategory.COMPLEXITY
    node_type = NodeType.FUNCTION_DEF

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("FunctionDef|AsyncFunctionDef")
            .where("__custom_condition__", arg_count_gt(self.MAX_ARGS))
        ]
        self.fixer_builders = [
            fix()
            .insert_comment(
                lambda node: (
                    f"# Function has {function_arg_count(node)} parameters "
                    f"(recommended <= {self.MAX_ARGS}). "
                    "Consider grouping related parameters into an object/dataclass "
                    "or splitting the function into smaller responsibilities."
                )
            )
            .because("Function has too many parameters.")
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
    id = "STRUCTURE-001"
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
            .insert_comment(
                lambda node: (
                    f"# Nesting depth >= {self.MAX_DEPTH}. "
                    "Consider guard clauses, early return/continue, "
                    "or extracting nested logic into a helper."
                )
            )
            .because("Control flow is nested too deeply.")
        ]


__all__ = [
    "TooManyArguments",
    "TooDeepNesting",
]