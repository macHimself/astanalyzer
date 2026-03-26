"""
Public matcher DSL for AST-based static analysis.

This module defines the main ``Matcher`` class and the ``match()`` factory
used to build chainable rules over astroid nodes.

The public API focuses on readability and composability. It allows callers to
describe structural, attribute-based and contextual conditions over Python AST
nodes without writing low-level traversal logic directly.

Typical usage:
    - create a matcher with ``match("If")``
    - refine it with conditions such as ``where(...)`` or ``has(...)``
    - evaluate it against nodes or walk a tree with ``find_matches()``

Implementation details such as AST traversal and condition dispatch are split
into helper modules to keep this module focused on the DSL itself.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from astroid import nodes

from .matcher_ast import (
    children_of,
    collect_used_names,
    contains_type,
    find_parent,
    find_parent_of_type,
    get_assign_target_name,
    get_attr,
    get_call_name,
    get_call_qual,
    get_constant_target_name,
    get_descendants,
    get_doc,
    later_in_block,
    next_sibling,
    previous_sibling,
    resolve_arg_value,
    siblings,
    siblings_after,
    split_types,
    walk,
)
from .matcher_conditions import (
    compare,
    evaluate_condition,
    evaluate_special_condition,
    expr_text,
    is_unnecessary_copy_call,
    resolve_ref,
    special_handlers,
)
from .matcher_types import MatchResult, Ref, ref
from .node_selector import NodeSelectorInput, resolve_node_selector
from .predicates import Predicate
from .tools import (
    _is_none_const,
    _iter_compare_pairs,
    has_long_lines,
    has_multiple_returns,
    has_redundant_else_after_terminal,
    is_empty_block,
    is_module_constant,
    is_unused_assign,
)

log = logging.getLogger(__name__)


class Matcher:
    """Chainable matcher for astroid nodes.

    A matcher represents a set of constraints that an AST node must satisfy.
    Constraints may target:

    - node type
    - attributes
    - parent relationships
    - descendants
    - sibling order
    - custom predicates

    Matchers are designed to be composed fluently:

        match("If").where("test", ...).with_descendant(match("Call"))

    The matcher API is intended for rule authors who want to describe static
    analysis patterns declaratively instead of implementing traversal logic
    manually.
    """

    def __init__(self, node_type: NodeSelectorInput):
        self.expected_type = node_type
        self.allowed_types = resolve_node_selector(node_type)

        self.depth = 1
        self.max_depth_limit = None

        self.subrules: list[Any] = []
        self.negative_subrules: list[str] = []
        self.conditions: list[dict[str, Any]] = []

        self.and_matcher: Matcher | None = None
        self.or_matcher: Matcher | None = None

        self.check_usage = False
        self.used_names: set[str] = set()

        self.negated = False
        self.captures: list[tuple[str, str | None]] = []

        self.descendant_rules: list[dict[str, Any]] = []
        self.scope_rules: list[dict[str, Any]] = []
        self.sequence_rules: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # DSL / builder API
    # ------------------------------------------------------------------

    def and_(self, other_matcher: "Matcher") -> "Matcher":
        self.and_matcher = other_matcher
        return self

    def or_(self, other_matcher: "Matcher") -> "Matcher":
        self.or_matcher = other_matcher
        return self

    def not_(self) -> "Matcher":
        self.negated = not self.negated
        return self

    def has(self, child_type: str) -> "Matcher":
        self.subrules.append(child_type)
        return self

    def missing(self, child_type: str) -> "Matcher":
        self.negative_subrules.append(child_type)
        return self

    def with_child(self, matcher: "Matcher") -> "Matcher":
        self.subrules.append(matcher)
        return self

    def max_depth(self, n: int = 1) -> "Matcher":
        nested = Matcher(self.expected_type)
        nested.depth = n
        self.max_depth_limit = n
        self.with_child(nested)
        return self

    def capture(self, name: str, path: str | None = None) -> "Matcher":
        self.captures.append((name, path))
        return self

    def capture_parent(self, name: str, parent_type: str | None = None) -> "Matcher":
        self.conditions.append(
            {
                "__capture_parent__": {
                    "name": name,
                    "type": parent_type,
                }
            }
        )
        return self

    def capture_ancestor(self, name: str, ancestor_type: str) -> "Matcher":
        self.conditions.append(
            {
                "__capture_ancestor__": {
                    "name": name,
                    "type": ancestor_type,
                }
            }
        )
        return self

    def where(self, attr: str, expected: Any = None, **kwargs) -> "Matcher":
        if expected is not None:
            self.conditions.append({attr: expected})
        for k, v in kwargs.items():
            self.conditions.append({k: v})
        return self

    def where_exists(self, attr: str) -> "Matcher":
        self.conditions.append({"__exists__": attr})
        return self

    def where_missing(self, attr: str) -> "Matcher":
        self.conditions.append({"__missing_attr__": attr})
        return self

    def where_regex(self, attr: str, pattern: str) -> "Matcher":
        self.conditions.append(
            {
                "__regex__": {
                    "attr": attr,
                    "pattern": pattern,
                }
            }
        )
        return self

    def where_len(self, attr: str, expected: int) -> "Matcher":
        self.conditions.append(
            {
                "__len__": {
                    "attr": attr,
                    "expected": expected,
                }
            }
        )
        return self

    def where_node_type(self, attr: str, expected_type: str) -> "Matcher":
        self.conditions.append(
            {
                "__node_type__": {
                    "attr": attr,
                    "expected": expected_type,
                }
            }
        )
        return self

    def where_same(self, attr: str, other: Any) -> "Matcher":
        self.conditions.append(
            {
                "__same__": {
                    "left": attr,
                    "right": other,
                }
            }
        )
        return self

    def where_not_same(self, attr: str, other: Any) -> "Matcher":
        self.conditions.append(
            {
                "__not_same__": {
                    "left": attr,
                    "right": other,
                }
            }
        )
        return self

    def where_same_text(self, attr: str, other: Any) -> "Matcher":
        self.conditions.append(
            {
                "__same_text__": {
                    "left": attr,
                    "right": other,
                }
            }
        )
        return self

    def where_call(self, *, name=None, qual=None) -> "Matcher":
        if name is not None:
            self.conditions.append({"__call_name__": name})
        if qual is not None:
            self.conditions.append({"__call_qual__": qual})
        return self

    def where_call_name(self, name: str) -> "Matcher":
        self.conditions.append({"__call_name__": name})
        return self

    def where_call_qual(self, qual: str) -> "Matcher":
        self.conditions.append({"__call_qual__": qual})
        return self

    def has_parent(self, parent_type: str) -> "Matcher":
        self.conditions.append({"__has_parent__": parent_type})
        return self

    def missing_parent(self, parent_type: str) -> "Matcher":
        self.conditions.append({"__missing_parent__": parent_type})
        return self

    def has_arg(self, kind, expected, index=0) -> "Matcher":
        self.conditions.append({f"__arg_{index}_{kind}__": expected})
        return self

    def satisfies(self, predicate) -> "Matcher":
        self.conditions.append({"__custom_condition__": predicate})
        return self

    def with_descendant(self, matcher: "Matcher", max_depth: int | None = None) -> "Matcher":
        self.descendant_rules.append(
            {
                "matcher": matcher,
                "max_depth": max_depth,
                "negated": False,
            }
        )
        return self

    def without_descendant(self, matcher: "Matcher", max_depth: int | None = None) -> "Matcher":
        self.descendant_rules.append(
            {
                "matcher": matcher,
                "max_depth": max_depth,
                "negated": True,
            }
        )
        return self

    def in_attr(self, attr_name: str, matcher: "Matcher", max_depth: int | None = None) -> "Matcher":
        self.scope_rules.append(
            {
                "attr": attr_name,
                "matcher": matcher,
                "max_depth": max_depth,
                "negated": False,
            }
        )
        return self

    def in_test(self, matcher: "Matcher", max_depth: int | None = None) -> "Matcher":
        return self.in_attr("test", matcher, max_depth=max_depth)

    def in_body(self, matcher: "Matcher", max_depth: int | None = None) -> "Matcher":
        return self.in_attr("body", matcher, max_depth=max_depth)

    def in_orelse(self, matcher: "Matcher", max_depth: int | None = None) -> "Matcher":
        return self.in_attr("orelse", matcher, max_depth=max_depth)

    def next_sibling(self, matcher: "Matcher") -> "Matcher":
        self.sequence_rules.append({"kind": "next_sibling", "matcher": matcher})
        return self

    def previous_sibling(self, matcher: "Matcher") -> "Matcher":
        self.sequence_rules.append({"kind": "previous_sibling", "matcher": matcher})
        return self

    def later_in_block(self, matcher: "Matcher") -> "Matcher":
        self.sequence_rules.append({"kind": "later_in_block", "matcher": matcher})
        return self

    def where_test_reason(self, *, any: bool = True) -> "Matcher":
        self.conditions.append({"__test_reason__": "any" if any else "none"})
        return self

    def where_compare(self, *, op_in=None, any_side_value=object()) -> "Matcher":
        self.conditions.append(
            {
                "__cmp__": {
                    "op_in": tuple(op_in) if op_in else None,
                    "any_side_value": any_side_value,
                }
            }
        )
        return self

    def where_compare_pairwise(self, *, op_in, any_side_value) -> "Matcher":
        self.conditions.append(
            {
                "__cmp_pair__": {
                    "op_in": tuple(op_in),
                    "any_side_value": any_side_value,
                }
            }
        )
        return self

    def where_contains(
        self,
        type_name: str,
        *,
        in_: str | None = None,
        max_depth: int | None = None,
    ) -> "Matcher":
        self.conditions.append(
            {
                "__contains__": {
                    "type": type_name,
                    "in": in_,
                    "max_depth": max_depth,
                }
            }
        )
        return self

    def where_target_name(self, *, exists: bool = True) -> "Matcher":
        self.conditions.append({"__assign_target_name__": "any" if exists else "none"})
        return self

    def overwritten_without_use_in_same_block(self) -> "Matcher":
        self.conditions.append({"__overwritten_without_use__": True})
        return self

    def where_except_binds_name(self, *, ignore: str | None = None) -> "Matcher":
        self.conditions.append({"__except_binds_name__": ignore})
        return self

    def where_body_missing_name(self, name_ref: str) -> "Matcher":
        self.conditions.append({"__body_missing_name__": name_ref})
        return self

    def where_defaults_contain(self, *, type_in: str) -> "Matcher":
        self.conditions.append({"__defaults_contain_type__": type_in})
        return self

    def where_defaults_contain_call(self, *, name_in) -> "Matcher":
        self.conditions.append({"__defaults_contain_call__": tuple(name_in)})
        return self

    def where_target_contains_any(self, *needles: str) -> "Matcher":
        self.conditions.append({"__target_contains_any__": tuple(needles)})
        return self

    def where_value_is_string_literal(self, *, non_empty: bool = True) -> "Matcher":
        self.conditions.append({"__value_is_string_literal__": non_empty})
        return self

    def where_mutable_default_argument(self) -> "Matcher":
        self.conditions.append({"__mutable_default_argument__": True})
        return self

    def same_iter_as_ancestor(self, ancestor_name: str) -> "Matcher":
        return self.where_same_text("iter", ref(f"{ancestor_name}.iter"))

    # ------------------------------------------------------------------
    # DSL sugar
    # ------------------------------------------------------------------

    def line_too_long(self, max_len: int = 100) -> "Matcher":
        return self.where("__custom_condition__", lambda node: has_long_lines(node, max_len))

    def multiple_returns(self) -> "Matcher":
        return self.where("__custom_condition__", has_multiple_returns)

    def redundant_else_after_terminal(self) -> "Matcher":
        return self.where("__custom_condition__", has_redundant_else_after_terminal)

    def empty_block(self) -> "Matcher":
        return self.where("__custom_condition__", is_empty_block)

    def is_unused(self) -> "Matcher":
        return self.where("__custom_condition__", is_unused_assign)

    def missing_blank_before(self) -> "Matcher":
        from .tools import missing_blank_before_def
        return self.where("__custom_condition__", missing_blank_before_def)

    def missing_docstring(self) -> "Matcher":
        return self.where_missing("doc")

    def has_docstring(self) -> "Matcher":
        return self.where_exists("doc")

    def name_not_snake_old(self) -> "Matcher":
        self.conditions.append(
            {
                "name": Predicate(
                    lambda actual, node: isinstance(actual, str)
                    and not re.match(r"^[a-z_][a-z0-9_]*$", actual)
                )
            }
        )
        return self

    def constant_name_not_upper(self) -> "Matcher":
        return self.where(
            "__custom_condition__",
            lambda node: (
                is_module_constant(node)
                and isinstance(self._get_constant_target_name(node), str)
                and not re.match(r"^[A-Z][A-Z0-9_]*$", self._get_constant_target_name(node))
            ),
        )

    def name_not_pascal(self) -> "Matcher":
        return self.where(
            "__custom_condition__",
            lambda node: isinstance(getattr(node, "name", None), str)
            and not re.match(r"^[A-Z][a-zA-Z0-9]+$", node.name),
        )

    def name_not_snake(self) -> "Matcher":
        return self.where(
            "__custom_condition__",
            lambda node: isinstance(getattr(node, "name", None), str)
            and not re.match(r"^[a-z_][a-z0-9_]*$", node.name),
        )

    def missing_module_docstring(self) -> "Matcher":
        return self.where(
            "__custom_condition__",
            lambda node: node.__class__.__name__ == "Module" and self._get_doc(node) is None,
        )

    def unnecessary_copy(self) -> "Matcher":
        return self.where("__custom_condition__", self._is_unnecessary_copy_call)

    # ------------------------------------------------------------------
    # Public execution API
    # ------------------------------------------------------------------

    def matches(self, node: nodes.NodeNG) -> bool:
        return self.evaluate(node, {})

    def find_matches(self, tree):
        matches = []
        if self.check_usage:
            self.used_names = self._collect_used_names(tree)

        def do_walk(node):
            if self.evaluate(node, {}):
                matches.append(node)
            for child in self._children_of(node):
                do_walk(child)

        do_walk(tree)
        return matches

    def evaluate(self, node, context: dict[str, Any] | None = None) -> bool:
        return self.match_result(node, context) is not None

    def match_result(self, node, context: dict[str, Any] | None = None) -> MatchResult | None:
        local_ctx = {} if context is None else dict(context)

        result = self._evaluate_core(node, local_ctx)
        if self.negated:
            result = not result

        if not result:
            return None

        refs = {k: v for k, v in local_ctx.items() if k not in {"module", "project"}}
        return MatchResult(node=node, refs=refs)

    # ------------------------------------------------------------------
    # Core matching
    # ------------------------------------------------------------------

    def _evaluate_core(self, node, context: dict[str, Any]) -> bool:
        local_result = (
            self._match_node_type(node)
            and self._apply_captures(node, context)
            and self._match_conditions(node, context)
            and self._match_negative_subrules(node)
            and self._match_subrules(node, context)
            and self._match_descendant_rules(node, context)
            and self._match_scope_rules(node, context)
            and self._match_sequence_rules(node, context)
            and (not self.and_matcher or self.and_matcher.evaluate(node, context.copy()))
        )

        if self.or_matcher:
            return local_result or self.or_matcher.evaluate(node, context.copy())

        return local_result

    def _match_node_type(self, node) -> bool:
        return node.__class__.__name__ in self._split_types(self.expected_type)

    def _match_conditions(self, node, context: dict[str, Any]) -> bool:
        for cond in self.conditions:
            for attr, expected in cond.items():
                if not self._evaluate_condition(node, attr, expected, context):
                    return False
        return True

    def _match_negative_subrules(self, node) -> bool:
        children = list(self._children_of(node))
        for disallowed in self.negative_subrules:
            if any(child.__class__.__name__ == disallowed for child in children):
                return False
        return True

    def _match_subrules(self, node, context: dict[str, Any]) -> bool:
        children = list(self._children_of(node))
        siblings_after_list = self._siblings_after(node)

        for rule in self.subrules:
            if rule == "ANY_SIBLING":
                if not siblings_after_list:
                    return False
                continue

            if isinstance(rule, str):
                if not any(child.__class__.__name__ == rule for child in children):
                    return False
                continue

            if isinstance(rule, Matcher):
                descendants = self._get_descendants(node, rule.depth)
                if not any(rule.evaluate(desc, context.copy()) for desc in descendants):
                    return False
                continue

        return True

    def _match_descendant_rules(self, node, context: dict[str, Any]) -> bool:
        for spec in self.descendant_rules:
            matcher = spec["matcher"]
            max_depth = spec["max_depth"]
            negated = spec["negated"]

            found = any(
                matcher.evaluate(desc, context.copy())
                for desc, depth in self._walk(node, max_depth=max_depth)
                if depth > 0
            )

            if negated and found:
                return False
            if not negated and not found:
                return False

        return True

    def _match_scope_rules(self, node, context: dict[str, Any]) -> bool:
        for spec in self.scope_rules:
            start = self._get_attr(node, spec["attr"])
            matcher = spec["matcher"]
            max_depth = spec["max_depth"]
            negated = spec["negated"]

            found = False
            for sub, _depth in self._walk(start, max_depth=max_depth):
                if sub is None:
                    continue
                if matcher.evaluate(sub, context.copy()):
                    found = True
                    break

            if negated and found:
                return False
            if not negated and not found:
                return False

        return True

    def _match_sequence_rules(self, node, context: dict[str, Any]) -> bool:
        for spec in self.sequence_rules:
            kind = spec["kind"]
            matcher = spec["matcher"]

            if kind == "next_sibling":
                sib = self._next_sibling(node)
                if sib is None:
                    return False
                result = matcher.match_result(sib, context.copy())
                if result is None:
                    return False
                context.update(result.refs)
                continue

            if kind == "previous_sibling":
                sib = self._previous_sibling(node)
                if sib is None:
                    return False
                result = matcher.match_result(sib, context.copy())
                if result is None:
                    return False
                context.update(result.refs)
                continue

            if kind == "later_in_block":
                matched = False
                for item in self._later_in_block(node):
                    result = matcher.match_result(item, context.copy())
                    if result is not None:
                        context.update(result.refs)
                        matched = True
                        break
                if not matched:
                    return False
                continue

            return False

        return True

    # ------------------------------------------------------------------
    # Delegates: condition logic
    # ------------------------------------------------------------------

    def _evaluate_condition(self, node, attr, expected, context: dict[str, Any]) -> bool:
        return evaluate_condition(self, node, attr, expected, context)

    def _evaluate_special_condition(self, node, attr, expected, context: dict[str, Any]) -> bool:
        return evaluate_special_condition(self, node, attr, expected, context)

    def _special_handlers(self):
        return special_handlers(self)

    def _resolve_ref(self, value: Any, context: dict[str, Any]) -> Any:
        return resolve_ref(self, value, context)

    def _compare(self, actual, expected, node, context: dict[str, Any] | None = None) -> bool:
        return compare(self, actual, expected, node, context)

    def _expr_text(self, value: Any) -> str | None:
        return expr_text(value)

    # ------------------------------------------------------------------
    # Delegates: AST helpers
    # ------------------------------------------------------------------

    def _children_of(self, node) -> list[Any]:
        return children_of(node)

    def _walk(self, root, max_depth: int | None = None):
        return walk(self, root, max_depth=max_depth)

    def _get_descendants(self, node, depth):
        return get_descendants(self, node, depth)

    def _siblings_after(self, node):
        return siblings_after(node)

    def _siblings(self, node):
        return siblings(node)

    def _next_sibling(self, node):
        return next_sibling(node)

    def _previous_sibling(self, node):
        return previous_sibling(node)

    def _later_in_block(self, node):
        return later_in_block(node)

    def _split_types(self, t) -> set[str]:
        return split_types(t)

    def _find_parent(self, node):
        return find_parent(node)

    def _find_parent_of_type(self, node, parent_type: str | None):
        return find_parent_of_type(node, parent_type)

    def _has_parent_type(self, node, parent_type) -> bool:
        return self._find_parent_of_type(node, parent_type) is not None

    def _get_doc(self, n):
        return get_doc(n)

    def _get_attr(self, node, dotted):
        return get_attr(node, dotted)

    def _resolve_arg_value(self, node, attr):
        return resolve_arg_value(self, node, attr)

    def _get_call_name(self, node):
        return get_call_name(node)

    def _get_call_qual(self, node):
        return get_call_qual(node)

    def _get_constant_target_name(self, node) -> str | None:
        return get_constant_target_name(node)

    def _get_assign_target_name(self, node) -> str | None:
        return get_assign_target_name(node)

    def _collect_used_names(self, tree):
        return collect_used_names(self, tree)

    # ------------------------------------------------------------------
    # Local helpers still kept here
    # ------------------------------------------------------------------

    def _is_unnecessary_copy_call(self, node) -> bool:
        return is_unnecessary_copy_call(self, node)

    def _apply_captures(self, node, context: dict[str, Any]) -> bool:
        for name, path in self.captures:
            value = node if path is None else self._get_attr(node, path)
            if value is None:
                return False
            context[name] = value
        return True


def match(node_type: NodeSelectorInput) -> Matcher:
    """Create a matcher for the given node selector.

    Args:
        node_type: Selector describing accepted AST node types. This may be
            a node class, a string such as ``"If"``, or a union such as
            ``"If|For|While"``.

    Returns:
        A new ``Matcher`` instance.
    """
    return Matcher(node_type)