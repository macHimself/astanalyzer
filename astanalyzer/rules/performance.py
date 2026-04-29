"""
Performance and efficiency rules for astanalyzer.

This module defines static analysis rules focused on inefficient constructs,
unnecessary work, and patterns that may hurt readability or runtime behaviour
in Python code.

The rules in this module target cases such as:
- list comprehensions used only for side effects
- unnecessary copies of values or iterables
- redundant sorting before `min()` or `max()`
- nested iteration over the same collection
- loops that could be rewritten as comprehensions
- inefficient use of `str.join(...)`

These rules are intentionally pragmatic:
- some findings offer direct rewrites
- some only add advisory comments because safe automatic refactoring would
  require deeper semantic knowledge
- the goal is to surface likely inefficiencies without pretending to prove
  actual performance bottlenecks

The rules operate on `astroid` AST nodes and are expressed using the matcher DSL
and fixer DSL provided by astanalyzer.
"""

from __future__ import annotations

from ..enums import NodeType, RuleCategory, Severity
from ..fixer import fix
from ..matcher import match
from ..rule import Rule
from ..tools import (
    is_loop_comprehension_candidate,
    loop_comprehension_suggestion,
    is_builtin_print_call,
    is_redundant_sorted_before_minmax,
    is_probably_str_join_call,
    is_nested_loop_same_stable_collection
)


class PrintInListComprehension(Rule):
    """
    WHAT:
    Detects list comprehensions that call print() as their produced element.

    WHY:
    List comprehensions are intended to build lists. Using them only to execute
    side effects makes the code harder to read and creates an unnecessary
    intermediate list whose values are usually discarded.

    WHEN:
    This is problematic when the comprehension is used as a standalone expression
    or when the resulting list is not needed. It is especially relevant in scripts,
    debugging code, and data-processing loops. If the list of return values is
    intentionally used, the code should be reviewed manually.

    HOW:
    Replace the list comprehension with an explicit for loop. A for loop makes
    the side effect clear and avoids constructing an unused list.

    LIMITATIONS:
    This rule assumes the list produced by the comprehension is not used.
    If the list is intentionally consumed later, this may be a false positive.
    """
    id = "PERF-001"
    title = "Print used inside list comprehension for side effects"
    severity = Severity.WARNING
    category = RuleCategory.PERFORMANCE
    node_type = NodeType.EXPR

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Expr").in_attr(
                "value",
                match("ListComp").in_attr(
                    "elt",
                    match("Call").satisfies(is_builtin_print_call),
                ),
            )
        ]
        self.fixer_builders = [
            fix()
            .replace_print_listcomp_with_for_loop()
            .because("Replace side-effect list comprehension with explicit for loop.")
        ]


class UselessListComprehension(Rule):
    """
    WHAT:
    Detects list comprehensions that call print() as their produced element.

    WHY:
    List comprehensions are intended to build lists. Using them only to execute
    side effects makes the code harder to read and creates an unnecessary
    intermediate list whose values are usually discarded.

    WHEN:
    This is problematic when the comprehension is used as a standalone expression
    or when the resulting list is not needed. It is especially relevant in scripts,
    debugging code, and data-processing loops. If the list of return values is
    intentionally used, the code should be reviewed manually.

    HOW:
    Replace the list comprehension with an explicit for loop. A for loop makes
    the side effect clear and avoids constructing an unused list.

    LIMITATIONS:
    This rule cannot reliably determine whether the result is used indirectly
    (e.g. debugging, REPL usage, or framework-driven execution).
    """
    id = "PERF-002"
    title = "Useless list comprehension (unused result)"
    severity = Severity.WARNING
    category = RuleCategory.PERFORMANCE
    node_type = NodeType.EXPR

    def __init__(self):
        super().__init__()
        self.matcher = match("Expr").has("ListComp")
        self.fixer_builders = [
            fix()
            .add_review_note_and_ignore(
                "PERF-002",
                "Useless list comprehension: result is unused. "
                "Use a for loop for side effects or assign/return the list.",
            )
            .because(
                "Add a review note and suppress this advisory performance finding "
                "to avoid repeated detection."
            )
        ]


class RedundantSortBeforeMinMax(Rule):
    """
    WHAT:
    Detects calls where sorted() is passed directly to min() or max().

    WHY:
    Sorting the entire iterable is unnecessary when only the minimum or maximum
    value is needed. min() and max() already scan the iterable and avoid the
    extra cost of sorting.

    WHEN:
    This is problematic for larger collections or performance-sensitive code,
    where sorting adds avoidable time and memory overhead. It may be intentional
    only if the sorted result is reused elsewhere, which is not the case when it
    is passed directly into min() or max().

    HOW:
    Call min() or max() directly on the original iterable. Preserve any key or
    default arguments where applicable.

    LIMITATIONS:
    This rule assumes the sorted result is not reused. If sorting is intended
    for readability or reuse, removing it may not be appropriate.
    """
    id = "PERF-003"
    title = "Redundant sort before min/max"
    severity = Severity.WARNING
    category = RuleCategory.PERFORMANCE
    node_type = NodeType.CALL

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Call").satisfies(is_redundant_sorted_before_minmax)
        ]
        self.fixer_builders = [
            fix()
            .remove_redundant_sorted()
            .because("Calling sorted() before min() or max() is redundant.")
        ]


class UnnecessaryCopy(Rule):
    """
    WHAT:
    Detects copy operations that appear to wrap an object or iterable without a
    clear need.

    WHY:
    Unnecessary copies increase memory usage and add extra computation. They can
    also make the code misleading by suggesting that isolation or mutation safety
    is required when the original object could be used directly.

    WHEN:
    This is relevant when the copied value is only read or immediately passed to
    another operation that does not require a separate object. It may be incorrect
    to remove the copy when the original object can be mutated later, when aliasing
    matters, or when a defensive copy is intentionally used.

    HOW:
    Remove the redundant copy when the original object can be safely reused. If
    the copy is intentional for mutation isolation or API safety, keep it and
    document the reason or suppress the advisory finding.

    LIMITATIONS:
    This rule cannot determine intent. Copies may be required for mutation safety,
    defensive programming, or API guarantees.
    """
    id = "PERF-004"
    title = "Unnecessary copy of iterable or object"
    severity = Severity.INFO
    category = RuleCategory.PERFORMANCE
    node_type = NodeType.CALL

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Call").unnecessary_copy()
        ]
        self.fixer_builders = [
            fix()
            .replace_unnecessary_copy()
            .because("Redundant copy wrapper can be removed."),
            fix()
            .add_review_note_and_ignore(
                "PERF-004",
                "Unnecessary copy detected. Remove redundant wrapping if safe.",
            )
            .because(
                "Add a review note and suppress this advisory performance finding "
                "until manually reviewed."
            )
        ]


class DoubleLoopSameCollection(Rule):
    """
    WHAT:
    Detects nested loops that iterate over the same stable collection.

    WHY:
    Nested iteration over the same collection often creates quadratic time
    complexity. This can be acceptable for small inputs, but it becomes expensive
    as the collection grows and may hide a more efficient algorithmic approach.

    WHEN:
    This is most relevant in data processing, search, comparison, duplicate
    detection, and matching logic over larger collections. It may be intentional
    for pairwise comparison, matrix-like operations, or cases where every
    combination must be inspected.

    HOW:
    Review whether the nested loop can be replaced with a single pass, indexing,
    a set, a dictionary, grouping, or another data structure suited to lookup.
    If all pairwise combinations are genuinely required, keep the loop and
    document or suppress the advisory finding.

    LIMITATIONS:
    Nested iteration may be intentional for pairwise comparison, matrix-like
    operations, or algorithms that require full combination evaluation.
    """
    id = "PERF-005"
    title = "Nested loops over the same collection"
    severity = Severity.INFO
    category = RuleCategory.PERFORMANCE
    node_type = NodeType.FOR

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("For").where("__custom_condition__", is_nested_loop_same_stable_collection)
        ]
        self.fixer_builders = [
            fix()
            .add_review_note_and_ignore(
                "PERF-005",
                "Collection is iterated multiple times. Consider combining loops if it does not reduce readability or change side effects.",
            )
            .because(
                "Add a review note and suppress this advisory performance finding "
                "until the loop structure is manually reviewed."
            )
        ]


class LoopCouldBeComprehension(Rule):
    """
    WHAT:
    Detects simple loops that build a list, set, or dictionary and could likely
    be expressed as a comprehension.

    WHY:
    For straightforward collection construction, comprehensions are often more
    concise and idiomatic in Python. They can make the transformation from input
    to output clearer when the loop body is simple.

    WHEN:
    This is useful for simple append/add/assignment patterns without complex
    branching, side effects, or multi-step logic. It should not be applied when
    a normal loop is clearer, when debugging is easier with explicit statements,
    or when the loop performs meaningful side effects.

    HOW:
    Rewrite the loop as a list, set, or dictionary comprehension only if the result
    is easier to read. If the explicit loop communicates the logic better, keep it
    and suppress the advisory finding.

    LIMITATIONS:
    This rule is stylistic and heuristic. Comprehensions may reduce readability
    in complex logic or hinder debugging.
    """
    id = "PERF-006"
    title = "Loop could be a comprehension"
    severity = Severity.INFO
    category = RuleCategory.PERFORMANCE
    node_type = NodeType.FOR

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("For").where("__custom_condition__", is_loop_comprehension_candidate)
        ]
        self.fixer_builders = [
            fix()
            .add_review_note_and_ignore(
                "PERF-006",
                lambda node: (
                    f"Loop can be a {loop_comprehension_suggestion(node)[0]} comprehension. "
                    f"E.g.: {loop_comprehension_suggestion(node)[1]}"
                ),
            )
            .because(
                "Add a review note and suppress this advisory performance finding "
                "until manually reviewed."
            )
        ]


class JoinOnGenerator(Rule):
    """
    WHAT:
    Detects str.join() calls that receive a list comprehension or list-wrapped
    generator expression.

    WHY:
    join() can consume an iterable of strings directly. Building an intermediate
    list is usually unnecessary and can increase memory usage, especially when
    joining many values.

    WHEN:
    This is relevant when the list is created only for the join() call and is not
    used elsewhere. It is most useful for large iterables or repeated join
    operations. For very small inputs, the performance difference may be negligible.

    HOW:
    Pass a generator expression directly to join() instead of a list comprehension
    or list(...) wrapper. Keep the list only if it is intentionally reused or
    needed for debugging.

    LIMITATIONS:
    The performance gain is usually small. Using a list may be intentional
    for reuse, debugging, or clarity.
    """
    id = "PERF-007"
    title = "Use generator expression in join()"
    severity = Severity.INFO
    category = RuleCategory.PERFORMANCE
    node_type = NodeType.CALL

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Call")
            .satisfies(is_probably_str_join_call)
            .where_len("args", 1)
            .where_node_type("args.0", "ListComp"),

            match("Call")
            .satisfies(is_probably_str_join_call)
            .where_len("args", 1)
            .where_node_type("args.0", "Call")
            .where("args.0.func.name", "list")
            .where_len("args.0.args", 1)
            .where_node_type("args.0.args.0", "GeneratorExp"),
        ]
        self.fixer_builders = [
            fix()
            .replace_join_listcomp_with_generator()
            .because("Use a generator expression to avoid building an unnecessary list.")
        ]


__all__ = [
    "PrintInListComprehension",
    "UselessListComprehension",
    "RedundantSortBeforeMinMax",
    "UnnecessaryCopy",
    "DoubleLoopSameCollection",
    "LoopCouldBeComprehension",
    "JoinOnGenerator",
]
