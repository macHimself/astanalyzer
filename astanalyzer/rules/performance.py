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
)


class PrintInListComprehension(Rule):
    id = "COMP-024"
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
                    match("Call").where_call(name="print"),
                ),
            )
        ]
        self.fixer_builders = [
            fix()
            .replace_print_listcomp_with_for_loop()
            .because("Replace side-effect list comprehension with explicit for loop.")
        ]


class UselessListComprehension(Rule):
    id = "COMP-025"
    title = "Useless list comprehension (unused result)"
    severity = Severity.WARNING
    category = RuleCategory.PERFORMANCE
    node_type = NodeType.EXPR

    def __init__(self):
        super().__init__()
        self.matcher = match("Expr").has("ListComp")
        self.fixer_builders = [
            fix()
            .comment_before(
                "Useless list comprehension: result is unused. "
                "Use a for loop for side effects or assign/return the list."
            )
            .because("List comprehension result is computed but never used.")
        ]


class RedundantSortBeforeMinMax(Rule):
    id = "ALG-025"
    title = "Redundant sort before min/max"
    severity = Severity.WARNING
    category = RuleCategory.PERFORMANCE
    node_type = NodeType.CALL

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Call").where_call(name={"min", "max"}).has_arg("func", "sorted")
        ]
        self.fixer_builders = [
            fix()
            .remove_redundant_sorted()
            .because("Calling sorted() before min() or max() is redundant.")
        ]


class UnnecessaryCopy(Rule):
    id = "PERF-026"
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
            .comment_before("Unnecessary copy detected. Remove redundant wrapping.")
            .because("Redundant copy operation detected."),
        ]


class DoubleLoopSameCollection(Rule):
    id = "PERF-027"
    title = "Nested loops over the same collection"
    severity = Severity.INFO
    category = RuleCategory.PERFORMANCE
    node_type = NodeType.FOR

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("For")
            .capture_ancestor("outer", "For")
            .same_iter_as_ancestor("outer")
        ]
        self.fixer_builders = [
            fix()
            .insert_comment(
                lambda node: (
                    "# Nested loop iterates over the same collection as an outer loop. "
                    "Consider a single pass, indexing, a set for membership, or an algorithmic change."
                )
            )
            .because("Nested loops iterate over the same collection.")
        ]


class LoopCouldBeComprehension(Rule):
    id = "COMP-028"
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
            .insert_comment(
                lambda node: (
                    f"# Loop can be a {loop_comprehension_suggestion(node)[0]} comprehension. "
                    f"E.g.: {loop_comprehension_suggestion(node)[1]}"
                )
            )
            .because("This loop can likely be expressed as a comprehension.")
        ]


class JoinOnGenerator(Rule):
    id = "STR-029"
    title = "Use generator expression in join()"
    severity = Severity.INFO
    category = RuleCategory.PERFORMANCE
    node_type = NodeType.CALL

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Call")
            .where_call(name="join")
            .where_len("args", 1)
            .where_node_type("args.0", "ListComp"),

            match("Call")
            .where_call(name="join")
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