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
    WHAT:
    Detects assignments where the assigned variable is never used.

    WHY:
    Unused variables introduce noise into the code and make it harder to
    understand what values are actually relevant. They may also indicate
    incomplete refactoring, forgotten logic, or mistakes where a value
    was computed but never applied.

    WHEN:
    This is problematic in most production code, especially in business logic,
    where unused values may hide missing functionality or incorrect assumptions.
    However, it may be intentional in cases such as debugging, placeholders,
    or when calling functions for their side effects.

    HOW:
    Remove the assignment if the value is not needed. If the expression has
    side effects (e.g. function calls), keep the expression and remove only
    the assignment. If the variable is intentionally unused, consider documenting
    it or suppressing the finding.

    LIMITATIONS:
    This rule may produce false positives when variables are intentionally unused
    (e.g. placeholders, debugging variables, or variables named '_'). It may also
    miss indirect usage through dynamic evaluation, reflection, or framework-specific
    mechanisms.
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
    WHAT:
    Detects statements that appear after a terminal control flow operation
    such as return, raise, break, or continue.

    WHY:
    Code after a terminal statement will never be executed, which makes it
    dead code. This can indicate logical errors, incomplete refactoring,
    or misplaced statements. Keeping unreachable code reduces clarity and
    may mislead readers about the actual behaviour of the program.

    WHEN:
    This is almost always a real issue, particularly in functions with
    complex control flow. Exceptions may include intentionally unreachable
    code used for debugging, documentation, or conditional execution patterns
    that are not statically visible, though such cases should be explicit.

    HOW:
    Remove the unreachable statements or restructure the control flow so that
    the intended logic is executed. Ensure that any important operations are
    placed before the terminal statement.

    LIMITATIONS:
    This rule assumes standard control flow and may produce false positives in cases
    where execution paths are controlled dynamically or through patterns not visible
    in static analysis (e.g. conditional imports, debugging constructs, or tooling).
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
    WHAT:
    Detects assignments where the assigned variable is never used, but the
    assigned expression may have side effects.

    WHY:
    Removing an unused assignment blindly can change program behaviour if
    the assigned expression performs side effects (e.g. function calls,
    I/O operations). This rule identifies such cases and allows preserving
    the expression while removing the unused variable.

    WHEN:
    This is relevant when the assigned value is unused but the right-hand
    side expression may still be important. It is especially useful in
    code that performs logging, mutations, or external calls as part of
    an assignment. It is less relevant for pure expressions without side
    effects.

    HOW:
    Replace the assignment with the original expression to preserve side
    effects while removing the unused variable. If no side effects are
    expected, the entire assignment can be safely removed. For complex
    assignments, manual review is recommended.

    LIMITATIONS:
    This rule relies on heuristics and cannot reliably determine whether an expression
    has side effects. Complex assignments, dynamic behaviour, or framework-specific
    patterns may require manual review before applying fixes.
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
