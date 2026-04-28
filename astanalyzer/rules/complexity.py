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
    WHAT:
    Detects functions or methods with more parameters than the configured limit.

    WHY:
    A long parameter list makes a function harder to understand, call correctly,
    test, and maintain. It can also indicate that the function has too many
    responsibilities or that several parameters belong to the same conceptual
    object.

    WHEN:
    This is most relevant for public APIs, frequently used functions, and functions
    where parameters represent related configuration or domain data. It may be less
    problematic for framework callbacks, generated code, thin wrappers, or functions
    that intentionally mirror an external API.

    HOW:
    Review whether related parameters can be grouped into a dataclass, configuration
    object, value object, or domain model. If the parameters belong to different
    responsibilities, split the function into smaller functions with clearer
    purposes. If the current signature is intentional, add a review note or suppress
    the advisory finding.
    """
    MAX_ARGS = 5
    id = "CX-001"
    title = "Function has too many parameters"
    severity = Severity.WARNING
    category = RuleCategory.COMPLEXITY
    node_type = NodeType.FUNCTION_DEF

    def __init__(self):
        super().__init__()
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
    WHAT:
    Detects control flow structures (if, for, while, try) that are nested deeper
    than the configured threshold. [3]

    WHY:
    Deep nesting increases cognitive complexity, making the code harder to read,
    understand, and reason about. It obscures the main execution path and makes
    edge cases harder to identify, test, and modify. Highly nested code is also
    more error-prone during future changes.

    WHEN:
    This is especially problematic in business logic, decision-heavy code, and
    long functions where multiple conditions and loops are combined. It may be
    acceptable in short, tightly scoped logic blocks or in code that naturally
    requires structured nesting (e.g. parsers or state machines), though even
    there readability should be carefully evaluated.

    HOW:
    Reduce nesting by introducing guard clauses (early returns/continues),
    flattening conditional structures, or extracting nested logic into separate
    helper functions. Focus on making the main execution path visible and easy
    to follow. If deep nesting is intentional, document the reasoning or suppress
    the advisory finding.
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
    WHAT:
    Detects functions or async functions whose relevant statement count exceeds
    the configured limit.

    WHY:
    Long functions are harder to read, understand, test, and safely modify. They
    often combine multiple responsibilities, which makes the function more fragile
    and increases the risk of introducing regressions during changes.

    WHEN:
    This is most relevant for business logic, data processing, validation, and
    functions that contain several distinct steps or branches. It may be less
    problematic for generated code, simple sequential setup code, or functions
    where splitting would only hide straightforward logic behind artificial helper
    names.

    HOW:
    Review the function for separate responsibilities or repeated logical phases.
    Extract coherent parts into smaller helper functions, move domain-specific
    operations into dedicated objects, or simplify branching before splitting. If
    the function is intentionally long and still clear, add a review note or
    suppress the advisory finding.
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
