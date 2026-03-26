"""
AST helpers for matcher internals.
"""

from __future__ import annotations

import ast
from typing import Any

from astroid import nodes as anodes
from .tools import _iter_compare_pairs


def children_of(node) -> list[Any]:
    return list(getattr(node, "get_children", lambda: [])())


def walk(matcher, root, max_depth: int | None = None):
    if root is None:
        return

    stack: list[tuple[Any, int]] = []
    if isinstance(root, (list, tuple)):
        for item in reversed(root):
            stack.append((item, 0))
    else:
        stack.append((root, 0))

    seen = set()

    while stack:
        cur, depth = stack.pop()
        if cur is None:
            continue

        oid = id(cur)
        if oid in seen:
            continue
        seen.add(oid)

        yield cur, depth

        if max_depth is not None and depth >= max_depth:
            continue

        for child in reversed(children_of(cur)):
            stack.append((child, depth + 1))


def get_descendants(matcher, node, depth):
    if depth <= 0:
        return []
    return [n for n, d in walk(matcher, node, max_depth=depth) if d > 0]


def siblings_after(node):
    parent = getattr(node, "parent", None)
    body = getattr(parent, "body", None)
    if not isinstance(body, list):
        return []
    try:
        idx = body.index(node)
    except ValueError:
        return []
    return body[idx + 1:]


def siblings(node):
    parent = getattr(node, "parent", None)
    body = getattr(parent, "body", None)
    if not isinstance(body, list):
        return []
    return body


def next_sibling(node):
    body = siblings(node)
    if not body:
        return None
    try:
        idx = body.index(node)
    except ValueError:
        return None
    return body[idx + 1] if idx + 1 < len(body) else None


def previous_sibling(node):
    body = siblings(node)
    if not body:
        return None
    try:
        idx = body.index(node)
    except ValueError:
        return None
    return body[idx - 1] if idx - 1 >= 0 else None


def later_in_block(node):
    body = siblings(node)
    if not body:
        return []
    try:
        idx = body.index(node)
    except ValueError:
        return []
    return body[idx + 1:]


def split_types(t) -> set[str]:
    if isinstance(t, str) and "|" in t:
        return {x.strip() for x in t.split("|") if x.strip()}
    if isinstance(t, str):
        return {t}
    return set()


def find_parent(node):
    return getattr(node, "parent", None)


def find_parent_of_type(node, parent_type: str | None):
    if parent_type is None:
        return getattr(node, "parent", None)

    allowed = split_types(parent_type)
    parent = getattr(node, "parent", None)

    while parent is not None:
        if parent.__class__.__name__ in allowed:
            return parent
        parent = getattr(parent, "parent", None)

    return None


def has_parent_type(node, parent_type) -> bool:
    return find_parent_of_type(node, parent_type) is not None


def get_doc(n):
    doc_node = getattr(n, "doc_node", None)
    if doc_node is not None:
        value = getattr(doc_node, "value", None)
        if isinstance(value, str):
            return value

    try:
        doc = getattr(n, "doc", None)
        if isinstance(doc, str):
            return doc
    except Exception:
        pass

    try:
        return ast.get_docstring(n)
    except Exception:
        return None


def attr_from(obj, part):
    if obj is None:
        return None
    if part == "doc":
        return get_doc(obj)
    if part.isdigit():
        idx = int(part)
        return obj[idx] if isinstance(obj, (list, tuple)) and 0 <= idx < len(obj) else None
    return getattr(obj, part, None)


def get_attr(node, dotted):
    cur = node
    for part in dotted.replace("__", ".").split("."):
        cur = attr_from(cur, part)
        if cur is None:
            break
    if isinstance(cur, anodes.Name):
        return cur.name
    return cur


def resolve_arg_value(matcher, node, attr):
    try:
        _, _, rest = attr.partition("__arg_")
        index_str, _, kind_part = rest.partition("_")
        index = int(index_str)
        kind = kind_part.rstrip("_")
    except Exception:
        return None

    args = getattr(node, "args", [])
    if len(args) <= index:
        return None

    arg = args[index]
    if kind == "func":
        if arg.__class__.__name__ != "Call":
            return None
        return get_call_name(arg)

    return get_attr(arg, kind)


def get_call_name(node):
    if node.__class__.__name__ != "Call":
        return None

    func = getattr(node, "func", None)
    if func is None:
        return None

    if func.__class__.__name__ == "Name":
        return getattr(func, "name", None) or getattr(func, "id", None)

    if func.__class__.__name__ == "Attribute":
        return (
            getattr(func, "attrname", None)
            or getattr(func, "attr", None)
            or getattr(func, "name", None)
        )

    return None


def get_call_qual(node):
    if node.__class__.__name__ != "Call":
        return None

    func = getattr(node, "func", None)
    if func is None:
        return None

    if func.__class__.__name__ == "Name":
        return getattr(func, "name", None) or getattr(func, "id", None)

    if func.__class__.__name__ != "Attribute":
        return None

    parts = []
    cur = func
    while cur is not None and cur.__class__.__name__ == "Attribute":
        attr = (
            getattr(cur, "attrname", None)
            or getattr(cur, "attr", None)
            or getattr(cur, "name", None)
        )
        if attr:
            parts.append(attr)
        cur = getattr(cur, "expr", None) or getattr(cur, "value", None)

    if cur is not None:
        base = getattr(cur, "name", None) or getattr(cur, "id", None)
        if base:
            parts.append(base)

    if not parts:
        return None

    return ".".join(reversed(parts))


def is_string_literal(value, *, non_empty: bool = True) -> bool:
    if value is None:
        return False

    cname = value.__class__.__name__
    if cname not in ("Const", "Constant", "Str", "Bytes"):
        return False

    v = getattr(value, "value", None)
    if not isinstance(v, (str, bytes)):
        return False

    return bool(str(v).strip()) if non_empty else True


def contains_type(matcher, root, type_in: str, *, max_depth: int | None = None) -> bool:
    allowed = split_types(type_in)
    for n, _depth in walk(matcher, root, max_depth=max_depth):
        if n.__class__.__name__ in allowed:
            return True
    return False


def contains_name(matcher, root, name: str) -> bool:
    if not name:
        return False
    for n, _ in walk(matcher, root):
        if n.__class__.__name__ == "Name":
            ident = getattr(n, "name", None) or getattr(n, "id", None)
            if ident == name:
                return True
    return False


def contains_call_name(matcher, root, names) -> bool:
    names = set(names)
    for n, _ in walk(matcher, root):
        if n.__class__.__name__ == "Call":
            nm = get_call_name(n)
            if nm in names:
                return True
    return False


def iter_function_defaults(fn):
    args = getattr(fn, "args", None)
    if not args:
        return []
    defaults = getattr(args, "defaults", []) or []
    kw_defaults = getattr(args, "kw_defaults", []) or []
    return [d for d in (defaults + kw_defaults) if d is not None]


def get_constant_target_name(node) -> str | None:
    cname = node.__class__.__name__
    if cname == "Assign":
        targets = getattr(node, "targets", []) or []
        if not targets:
            return None
        target = targets[0]
    elif cname == "AnnAssign":
        target = getattr(node, "target", None)
    else:
        return None

    if target is None:
        return None

    return getattr(target, "name", None) or getattr(target, "id", None)


def get_assign_target_name(node) -> str | None:
    cname = node.__class__.__name__

    if cname == "Assign":
        targets = getattr(node, "targets", []) or []
        target = targets[0] if targets else None
    elif cname == "AnnAssign":
        target = getattr(node, "target", None)
    else:
        return None

    if target is None:
        return None

    tname = target.__class__.__name__
    if tname in ("AssignName", "Name"):
        return getattr(target, "name", None) or getattr(target, "id", None)

    if tname in ("AssignAttr", "Attribute"):
        base = getattr(target, "expr", None) or getattr(target, "value", None)
        base_name = getattr(base, "name", None) or getattr(base, "id", None)
        attr = (
            getattr(target, "attrname", None)
            or getattr(target, "attr", None)
            or getattr(target, "name", None)
        )
        return f"{base_name}.{attr}" if base_name and attr else attr

    return None


def node_reads_name(matcher, root, name: str) -> bool:
    for n, _ in walk(matcher, root):
        if n.__class__.__name__ == "Name":
            ident = getattr(n, "name", None) or getattr(n, "id", None)
            if ident == name:
                return True
    return False


def find_previous_overwritten_assign(matcher, node):
    if node.__class__.__name__ != "Assign":
        return None

    name = get_assign_target_name(node)
    if not name:
        return None

    parent = getattr(node, "parent", None)
    body = getattr(parent, "body", None)
    if not isinstance(body, list):
        return None

    try:
        idx = body.index(node)
    except ValueError:
        return None

    prev_idx = None
    for i in range(idx - 1, -1, -1):
        prev = body[i]
        if prev.__class__.__name__ == "Assign" and get_assign_target_name(prev) == name:
            prev_idx = i
            break

    if prev_idx is None:
        return None

    for j in range(prev_idx + 1, idx):
        if node_reads_name(matcher, body[j], name):
            return None

    return body[prev_idx]


def is_overwritten_without_use(matcher, node) -> bool:
    return find_previous_overwritten_assign(matcher, node) is not None


def except_bound_name(node) -> str | None:
    if node.__class__.__name__ != "ExceptHandler":
        return None

    n = getattr(node, "name", None)
    if not n:
        return None

    if isinstance(n, str):
        return n

    return getattr(n, "name", None) or getattr(n, "id", None)


def test_reason(matcher, node) -> str | None:
    ntype = node.__class__.__name__
    if ntype not in ("If", "While"):
        return None

    test = getattr(node, "test", None)
    if test is None:
        return None

    val = getattr(test, "value", None)
    if isinstance(val, bool) and val is True:
        return "truthy literal (True)"
    if isinstance(val, (int, float, complex)) and val != 0:
        return "truthy literal (non-zero number)"
    if isinstance(val, (str, bytes)) and len(val) > 0:
        return "truthy literal (non-empty string/bytes)"

    tcn = test.__class__.__name__
    if tcn in ("List", "Tuple", "Set") and getattr(test, "elts", None):
        return "truthy literal (non-empty collection)"
    if tcn == "Dict" and getattr(test, "keys", None):
        return "truthy literal (non-empty dict)"

    if tcn == "UnaryOp":
        op = getattr(getattr(test, "op", None), "__class__", type("X", (), {})).__name__
        operand = getattr(test, "operand", None)
        if op == "Not" and isinstance(getattr(operand, "value", None), bool) and operand.value is False:
            return "not False"

    if tcn == "BoolOp":
        op = getattr(getattr(test, "op", None), "__class__", type("X", (), {})).__name__
        values = getattr(test, "values", []) or []
        for v in values:
            vv = getattr(v, "value", None)
            truthy = (
                (isinstance(vv, bool) and vv is True)
                or (isinstance(vv, (int, float, complex)) and vv != 0)
                or (isinstance(vv, (str, bytes)) and len(vv) > 0)
            )
            if truthy and op == "Or":
                return "X or True (truthy operand)"
            if truthy and op == "And":
                return "True and X (redundant truthy operand)"

    if tcn == "Compare":
        #pairs = list(matcher._iter_compare_pairs(test))
        pairs = list(_iter_compare_pairs(test))
        if len(pairs) == 1:
            op_name, left, right = pairs[0]
            lname = getattr(left, "name", None) or getattr(left, "id", None)
            rname = getattr(right, "name", None) or getattr(right, "id", None)
            if lname and rname and lname == rname and op_name in ("Eq", "Is"):
                return "X == X / X is X (tautology; NaN edge-case)"

    return None


def node_value(n):
    if n is None:
        return None

    cn = n.__class__.__name__
    if cn in ("Const", "Constant", "NameConstant"):
        return getattr(n, "value", None)
    if cn in ("Name", "AssignName"):
        return getattr(n, "name", None) or getattr(n, "id", None)
    if cn in ("Attribute", "AssignAttr"):
        return (
            getattr(n, "attrname", None)
            or getattr(n, "attr", None)
            or getattr(n, "name", None)
        )
    if isinstance(n, (str, bytes, int, float, complex, bool)):
        return n
    return n


def collect_used_names(matcher, tree):
    used = set()
    for n, _ in walk(matcher, tree):
        if isinstance(n, anodes.Name):
            used.add(n.name)
        elif isinstance(n, anodes.Attribute):
            used.add(n.attrname)
        elif isinstance(n, anodes.Call):
            nm = get_call_name(n)
            if nm:
                used.add(nm)
    return used


def value_of(obj):
    if obj is None:
        return None
    if isinstance(obj, anodes.Const):
        return obj.value
    if isinstance(obj, anodes.Name):
        return obj.name
    if isinstance(obj, anodes.Attribute):
        return obj.attrname
    if hasattr(obj, "value"):
        return getattr(obj, "value", None)
    if hasattr(obj, "n"):
        return getattr(obj, "n", None)
    if hasattr(obj, "s"):
        return getattr(obj, "s", None)
    return obj