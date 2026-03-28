"""
Dead-code and control-flow rules for astanalyzer.

This module contains rules that detect assignments or statements which
do not contribute to the program's observable behaviour, or code that
cannot be reached because control flow has already terminated.

The rules focus on patterns such as:
- assigned values that are never used
- unreachable statements after terminal flow operations

These rules may offer automatic fixes where the transformation is local
and predictable.
"""

from __future__ import annotations

from ..enums import NodeType, RuleCategory, Severity
from ..fixer import fix
from ..matcher import match
from ..rule import Rule


class UnusedVariable(Rule):
    """
    Assigned variable is never used.

    This may indicate dead code, a mistake, or leftover debugging logic.
    Keeping unused variables reduces code clarity and may hide logical issues.

    Consider removing the assignment or using the value if it is needed.
    """
    id = "DEAD-001"
    title = "Unused variable"
    severity = Severity.WARNING
    category = RuleCategory.DEAD_CODE
    node_type = NodeType.ASSIGN

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Assign").is_unused()
        ]
        self.fixer_builders = [
            fix()
            .delete_node()
            .because("Remove unused variable."),
            fix()
            .replace_with_value()
            .because("Keep side effects of the assigned expression, but remove the assignment."),
        ]


class UnreachableCode(Rule):
    """
    Unreachable code detected after a terminal statement.

    Code appearing after return, raise, break, or continue will never be executed.
    This may indicate a logical error, leftover code, or incorrect control flow.

    Consider removing or restructuring the unreachable code.
    """
    id = "DEAD-002"
    title = "Unreachable code after return/raise/break/continue"
    severity = Severity.WARNING
    category = RuleCategory.DEAD_CODE
    node_type = {
        NodeType.RETURN,
        NodeType.RAISE,
        NodeType.BREAK,
        NodeType.CONTINUE,
    }

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Return|Raise|Break|Continue").has("ANY_SIBLING")
        ]
        self.fixer_builders = [
            fix()
            .remove_dead_code_after()
            .because("Remove unreachable code after terminal statement."),
        ]


__all__ = [
    "UnusedVariable",
    "UnreachableCode",
]