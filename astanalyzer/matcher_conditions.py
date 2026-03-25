"""
Condition evaluation helpers for matcher internals.
"""

from __future__ import annotations

import re
from typing import Any

from .matcher_ast import (
    contains_call_name,
    contains_name,
    contains_type,
    except_bound_name,
    find_parent,
    find_parent_of_type,
    find_previous_overwritten_assign,
    get_assign_target_name,
    get_attr,
    get_call_name,
    get_call_qual,
    is_string_literal,
    iter_function_defaults,
    node_value,
    test_reason,
)
from .matcher_types import Ref


def resolve_ref(matcher, value: Any, context: dict[str, Any]) -> Any:
    if not isinstance(value, Ref):
        return value

    ref_name = value.name
    if "." not in ref_name:
        return context.get(ref_name)

    base_name, _, rest = ref_name.partition(".")
    base_obj = context.get(base_name)
    if base_obj is None:
        return None

    return get_attr(base_obj, rest)


def expr_text(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, str):
        return value.strip()

    try:
        return value.as_string().strip()
    except Exception:
        pass

    name = getattr(value, "name", None) or getattr(value, "id", None)
    if isinstance(name, str):
        return name.strip()

    attr = (
        getattr(value, "attrname", None)
        or getattr(value, "attr", None)
        or getattr(value, "name", None)
    )
    if isinstance(attr, str):
        return attr.strip()

    return str(value).strip()


def compare(matcher, actual, expected, node, context: dict[str, Any] | None = None) -> bool:
    context = {} if context is None else context
    expected = resolve_ref(matcher, expected, context)

    from .predicates import Predicate

    if isinstance(expected, Predicate):
        return expected(actual, node)

    if isinstance(expected, (set, list, tuple)):
        return actual in expected

    if isinstance(expected, str):
        low = expected.lower()
        if low == "any":
            return True
        if low == "none":
            return actual is None

    return actual == expected


def evaluate_condition(matcher, node, attr, expected, context: dict[str, Any]) -> bool:
    if attr.startswith("__"):
        return evaluate_special_condition(matcher, node, attr, expected, context)

    actual = get_attr(node, attr)
    return compare(matcher, actual, expected, node, context)


def evaluate_special_condition(matcher, node, attr, expected, context: dict[str, Any]) -> bool:
    handlers = special_handlers(matcher)

    if attr in handlers:
        return handlers[attr](node, expected, context)

    if attr == "__call_name__":
        return compare(matcher, get_call_name(node), expected, node, context)

    if attr == "__call_qual__":
        return compare(matcher, get_call_qual(node), expected, node, context)

    if attr.startswith("__arg_"):
        actual = matcher._resolve_arg_value(node, attr)
        return compare(matcher, actual, expected, node, context)

    return False


def special_handlers(matcher):
    return {
        "__has_parent__": lambda n, e, c: check_has_parent(matcher, n, e, c),
        "__missing_parent__": lambda n, e, c: check_missing_parent(matcher, n, e, c),
        "__custom_condition__": lambda n, e, c: check_custom_condition(matcher, n, e, c),
        "__target_contains_any__": lambda n, e, c: check_target_contains_any(matcher, n, e, c),
        "__value_is_string_literal__": lambda n, e, c: check_value_is_string_literal(matcher, n, e, c),
        "__test_reason__": lambda n, e, c: check_test_reason(matcher, n, e, c),
        "__cmp__": lambda n, e, c: check_compare(matcher, n, e, c),
        "__cmp_pair__": lambda n, e, c: check_compare_pairwise(matcher, n, e, c),
        "__contains__": lambda n, e, c: check_contains(matcher, n, e, c),
        "__assign_target_name__": lambda n, e, c: check_assign_target_name(matcher, n, e, c),
        "__overwritten_without_use__": lambda n, e, c: check_overwritten_without_use(matcher, n, e, c),
        "__except_binds_name__": lambda n, e, c: check_except_binds_name(matcher, n, e, c),
        "__body_missing_name__": lambda n, e, c: check_body_missing_name(matcher, n, e, c),
        "__defaults_contain_type__": lambda n, e, c: check_defaults_contain_type(matcher, n, e, c),
        "__defaults_contain_call__": lambda n, e, c: check_defaults_contain_call(matcher, n, e, c),
        "__exists__": lambda n, e, c: check_exists(matcher, n, e, c),
        "__missing_attr__": lambda n, e, c: check_missing_attr(matcher, n, e, c),
        "__regex__": lambda n, e, c: check_regex(matcher, n, e, c),
        "__mutable_default_argument__": lambda n, e, c: check_mutable_default_argument(matcher, n, e, c),
        "__capture_parent__": lambda n, e, c: check_capture_parent(matcher, n, e, c),
        "__capture_ancestor__": lambda n, e, c: check_capture_ancestor(matcher, n, e, c),
        "__same__": lambda n, e, c: check_same(matcher, n, e, c),
        "__not_same__": lambda n, e, c: check_not_same(matcher, n, e, c),
        "__same_text__": lambda n, e, c: check_same_text(matcher, n, e, c),
        "__len__": lambda n, e, c: check_len(matcher, n, e, c),
        "__node_type__": lambda n, e, c: check_node_type(matcher, n, e, c),
    }


def check_len(matcher, node, expected, context) -> bool:
    value = get_attr(node, expected["attr"])
    try:
        return len(value) == expected["expected"]
    except Exception:
        return False


def check_node_type(matcher, node, expected, context) -> bool:
    value = get_attr(node, expected["attr"])
    if value is None:
        return False
    allowed = matcher._split_types(expected["expected"])
    return value.__class__.__name__ in allowed


def check_capture_parent(matcher, node, expected, context) -> bool:
    parent_type = expected.get("type")
    parent = find_parent_of_type(node, parent_type) if parent_type else find_parent(node)
    if parent is None:
        return False
    context[expected["name"]] = parent
    return True


def check_capture_ancestor(matcher, node, expected, context) -> bool:
    ancestor = find_parent_of_type(node, expected["type"])
    if ancestor is None:
        return False
    context[expected["name"]] = ancestor
    return True


def check_same(matcher, node, expected, context) -> bool:
    left_value = get_attr(node, expected["left"])
    right_value = resolve_ref(matcher, expected["right"], context)
    return left_value == right_value


def check_not_same(matcher, node, expected, context) -> bool:
    left_value = get_attr(node, expected["left"])
    right_value = resolve_ref(matcher, expected["right"], context)
    return left_value != right_value


def check_same_text(matcher, node, expected, context) -> bool:
    left_value = get_attr(node, expected["left"])
    right_value = resolve_ref(matcher, expected["right"], context)
    return expr_text(left_value) == expr_text(right_value)


def check_has_parent(matcher, node, expected, context) -> bool:
    return matcher._has_parent_type(node, expected)


def check_missing_parent(matcher, node, expected, context) -> bool:
    return not matcher._has_parent_type(node, expected)


def check_custom_condition(matcher, node, expected, context) -> bool:
    try:
        return bool(expected(node))
    except Exception:
        return False


def check_exists(matcher, node, expected, context) -> bool:
    return get_attr(node, expected) is not None


def check_missing_attr(matcher, node, expected, context) -> bool:
    return get_attr(node, expected) is None


def check_regex(matcher, node, expected, context) -> bool:
    value = get_attr(node, expected["attr"])
    if value is None:
        return False
    return re.search(expected["pattern"], str(value)) is not None


def check_target_contains_any(matcher, node, expected, context) -> bool:
    target = get_assign_target_name(node)
    if not target:
        return False
    low = target.lower()
    return any(str(n).lower() in low for n in expected)


def check_value_is_string_literal(matcher, node, expected, context) -> bool:
    value = getattr(node, "value", None)
    return is_string_literal(value, non_empty=bool(expected))


def check_test_reason(matcher, node, expected, context) -> bool:
    reason = test_reason(matcher, node)
    if expected == "any":
        return reason is not None
    if expected == "none":
        return reason is None
    return reason == expected


def check_compare(matcher, node, expected, context) -> bool:
    if node.__class__.__name__ != "Compare":
        return False

    pairs = list(matcher._iter_compare_pairs(node))
    if not pairs:
        return False

    op_in = expected.get("op_in")
    sentinel = object()
    any_side_value = expected.get("any_side_value", sentinel)

    if op_in and not any(op_name in op_in for op_name, _, _ in pairs):
        return False

    if any_side_value is not sentinel:
        values = []
        for _, left, right in pairs:
            values.append(node_value(left))
            values.append(node_value(right))
        if not any(v is any_side_value for v in values):
            return False

    return True


def check_compare_pairwise(matcher, node, expected, context) -> bool:
    if node.__class__.__name__ != "Compare":
        return False

    found = False
    for op_name, left_n, right_n in matcher._iter_compare_pairs(node):
        if op_name not in expected["op_in"]:
            continue

        if expected["any_side_value"] is None:
            ok = matcher._is_none_const(left_n) or matcher._is_none_const(right_n)
        else:
            ok = (
                node_value(left_n) == expected["any_side_value"]
                or node_value(right_n) == expected["any_side_value"]
            )

        if ok:
            found = True
        else:
            return False

    return found


def check_contains(matcher, node, expected, context) -> bool:
    start = node
    if expected.get("in"):
        start = get_attr(node, expected["in"])
    return contains_type(matcher, start, expected["type"], max_depth=expected.get("max_depth"))


def check_assign_target_name(matcher, node, expected, context) -> bool:
    tname = get_assign_target_name(node)
    if expected == "any":
        return bool(tname)
    if expected == "none":
        return tname is None
    return tname == expected


def check_overwritten_without_use(matcher, node, expected, context) -> bool:
    previous_assign = find_previous_overwritten_assign(matcher, node)
    if previous_assign is None:
        return False
    context["previous_assign"] = previous_assign
    return True


def check_except_binds_name(matcher, node, expected, context) -> bool:
    name = except_bound_name(node)
    if not name:
        return False
    if expected and name == expected:
        return False
    context["except_name"] = name
    return True


def check_body_missing_name(matcher, node, expected, context) -> bool:
    if node.__class__.__name__ != "ExceptHandler":
        return False

    name = context.get("except_name") or except_bound_name(node)
    if not name:
        return False

    body = getattr(node, "body", []) or []
    return not any(contains_name(matcher, stmt, name) for stmt in body)


def check_defaults_contain_type(matcher, node, expected, context) -> bool:
    if node.__class__.__name__ != "FunctionDef":
        return False
    return any(contains_type(matcher, d, expected) for d in iter_function_defaults(node))


def check_defaults_contain_call(matcher, node, expected, context) -> bool:
    if node.__class__.__name__ != "FunctionDef":
        return False
    return any(contains_call_name(matcher, d, expected) for d in iter_function_defaults(node))


def mutable_default_factory(matcher, node) -> str | None:
    if node is None:
        return None

    cname = node.__class__.__name__
    if cname == "List":
        return "[]"
    if cname == "Dict":
        return "{}"
    if cname == "Set":
        try:
            return node.as_string().rstrip()
        except Exception:
            return "set()"

    if cname == "Call":
        call_name = get_call_name(node)
        if call_name == "list":
            return "list()"
        if call_name == "dict":
            return "dict()"
        if call_name == "set":
            return "set()"

    return None


def check_mutable_default_argument(matcher, node, expected, context) -> bool:
    if node.__class__.__name__ != "FunctionDef":
        return False

    args = getattr(node, "args", None)
    if args is None:
        return False

    defaults = getattr(args, "defaults", []) or []
    arg_nodes = getattr(args, "args", []) or []

    if defaults and arg_nodes:
        positional_params = arg_nodes[-len(defaults):]
        for arg_node, default_node in zip(positional_params, defaults):
            factory = mutable_default_factory(matcher, default_node)
            if factory is not None:
                context["mutable_arg_name"] = getattr(arg_node, "name", None)
                context["mutable_default_expr"] = factory
                context["mutable_default_node"] = default_node
                context["mutable_arg_kind"] = "positional"
                return True

    kwonlyargs = getattr(args, "kwonlyargs", []) or []
    kw_defaults = getattr(args, "kw_defaults", []) or []

    for arg_node, default_node in zip(kwonlyargs, kw_defaults):
        if default_node is None:
            continue
        factory = mutable_default_factory(matcher, default_node)
        if factory is not None:
            context["mutable_arg_name"] = getattr(arg_node, "name", None)
            context["mutable_default_expr"] = factory
            context["mutable_default_node"] = default_node
            context["mutable_arg_kind"] = "kwonly"
            return True

    return False


def is_unnecessary_copy_call(matcher, node) -> bool:
    if node.__class__.__name__ != "Call":
        return False

    outer_name = get_call_name(node)
    if outer_name not in {"list", "set", "dict", "copy", "deepcopy"}:
        return False

    args = getattr(node, "args", []) or []
    keywords = getattr(node, "keywords", []) or []

    if len(args) != 1 or keywords:
        return False

    first = args[0]
    first_type = first.__class__.__name__

    if first_type == "Call":
        inner_name = get_call_name(first)
        if outer_name in {"list", "set", "dict"} and inner_name == outer_name:
            return True

        if outer_name in {"copy", "deepcopy"}:
            inner_args = getattr(first, "args", []) or []
            inner_keywords = getattr(first, "keywords", []) or []
            if inner_name in {"list", "set", "dict"} and len(inner_args) == 1 and not inner_keywords:
                return False

    if outer_name == "list" and first_type in {"List", "ListComp"}:
        return True
    if outer_name == "set" and first_type in {"Set", "SetComp"}:
        return True
    if outer_name == "dict" and first_type == "Dict":
        return True
    if outer_name in {"copy", "deepcopy"} and first_type in {"List", "Set", "Dict", "ListComp", "SetComp"}:
        return True

    return False