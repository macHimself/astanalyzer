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

    The assignment can be safely removed if the value has no important side effects.
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
            .because("Remove unused variable.")
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


class UnusedAssignmentKeepValue(Rule):
    """
    Assigned variable is never used.

    This may indicate dead code, a mistake, or leftover debugging logic.
    Keeping unused variables reduces code clarity and may hide logical issues.

    The assignment is removed while preserving the original expression to keep side effects.
    """
    id = "DEAD-003"
    title = "Unused assignment (keep value)"
    severity = Severity.WARNING
    category = RuleCategory.DEAD_CODE
    node_type = NodeType.ASSIGN

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Assign").is_unused().satisfies(self.is_simple_single_name_assign)
        ]
        self.fixer_builders = [
            fix()
            .delete_node()
            .because("Remove unused variable."),
            fix()
            .replace_with_value()
            .because("Keep side effects of the assigned expression, but remove the assignment."),
        ]

    def is_simple_single_name_assign(self, node) -> bool:
        """
        Determine whether the assignment is a simple single-variable assignment.

        This helper returns True only for assignments of the form:
            x = expr

        It deliberately excludes more complex assignment patterns, including:
            - multiple targets:
                a = b = expr
            - unpacking:
                a, b = expr
                [a, b] = expr
            - attribute assignments:
                obj.x = expr
            - subscript assignments:
                arr[0] = expr

        Purpose:
            This function is primarily used as a safety guard for fixers that
            transform assignments (e.g. replacing an assignment with its value).
            By restricting matches to simple cases, it helps ensure that applying
            such transformations does not unintentionally change program semantics.

        Parameters:
            node:
                An astroid Assign node.

        Returns:
            bool:
                True if the node represents a simple single-name assignment,
                False otherwise.
        """
        targets = getattr(node, "targets", []) or []
        if len(targets) != 1:
            return False
        return targets[0].__class__.__name__ == "AssignName"


__all__ = [
    "UnusedVariable",
    "UnreachableCode",
]
