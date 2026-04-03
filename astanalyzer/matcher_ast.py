"""
Internal AST helper utilities used by the matcher DSL.

This module provides low-level helper functions for traversing AST nodes,
resolving attributes, inspecting calls and assignments, working with sibling
relationships, and evaluating matcher-specific structural conditions.

The helpers in this module are primarily intended for internal matcher
implementation and rule evaluation rather than direct public use.
"""

from __future__ import annotations

import ast
from typing import Any

from astroid import nodes as anodes
from .tools import _iter_compare_pairs


# ===== Traversal helpers =====
def children_of(node) -> list[Any]:
    """Return direct child nodes of an AST node, or an empty list if unavailable."""
    return list(getattr(node, "get_children", lambda: [])())


def walk(matcher, root, max_depth: int | None = None):
    """
    Traverse an AST subtree in depth-first order.

    The function yields pairs of `(node, depth)` starting from the given root.
    It supports both a single root node and a list or tuple of root nodes.
    Already visited objects are skipped to avoid repeated traversal.

    Args:
        matcher: Matcher instance requesting the traversal. Included for
            interface consistency with other matcher helpers.
        root: Root AST node or sequence of nodes to traverse.
        max_depth (int | None): Optional maximum traversal depth. If provided,
            descendants deeper than this limit are not visited.

    Yields:
        tuple[Any, int]: Traversed node and its depth relative to the root.
    """
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
    """
    Return descendant nodes up to the given depth.

    The root node itself is excluded from the result.
    """
    if depth <= 0:
        return []
    return [n for n, d in walk(matcher, node, max_depth=depth) if d > 0]


# ===== Parent / sibling helpers =====
def siblings_after(node):
    """Return sibling nodes that appear after the given node in the parent body."""
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
    """Return the parent body list containing the given node, if available."""
    parent = getattr(node, "parent", None)
    body = getattr(parent, "body", None)
    if not isinstance(body, list):
        return []
    return body


def next_sibling(node: Any) -> Any | None:
    """Return the next sibling of the given node, or None if there is none."""
    body = siblings(node)
    if not body:
        return None
    try:
        idx = body.index(node)
    except ValueError:
        return None
    return body[idx + 1] if idx + 1 < len(body) else None


def previous_sibling(node):
    """Return the previous sibling of the given node, or None if there is none."""
    body = siblings(node)
    if not body:
        return None
    try:
        idx = body.index(node)
    except ValueError:
        return None
    return body[idx - 1] if idx - 1 >= 0 else None


def later_in_block(node):
    """Return all sibling nodes that appear later in the same parent block."""
    body = siblings(node)
    if not body:
        return []
    try:
        idx = body.index(node)
    except ValueError:
        return []
    return body[idx + 1:]


# ===== Type selector helpers =====
def split_types(t: Any) -> set[str]:
    """
    Find the nearest parent whose class name matches the requested type selector.

    If `parent_type` is None, the direct parent is returned.
    """
    if isinstance(t, str) and "|" in t:
        return {x.strip() for x in t.split("|") if x.strip()}
    if isinstance(t, str):
        return {t}
    return set()


def find_parent(node: Any) -> Any | None:
    """Return the direct parent of a node, or None if not available."""
    return getattr(node, "parent", None)


def find_parent_of_type(node, parent_type: str | None):
    """
    Find the nearest parent node matching the given type selector.

    If `parent_type` is provided, the function walks up the parent chain
    and returns the first ancestor whose class name matches the selector.
    The selector may contain multiple types separated by '|'.

    If `parent_type` is None, the direct parent is returned.

    Args:
        node: AST node to start from.
        parent_type (str | None): Type selector (e.g. "If|For") or None.

    Returns:
        The matching parent node, or None if no match is found.
    """
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
    """
    Extract a docstring from a node using several compatible access strategies.

    Supports astroid-style doc nodes, direct `doc` attributes, and the
    standard library `ast.get_docstring` fallback.
    """
    return find_parent_of_type(node, parent_type) is not None


# ===== Attribute resolution helpers =====
def get_doc(n):
    """
    Extract a docstring from a node using multiple compatible strategies.

    The function attempts to retrieve a docstring in the following order:
    1. astroid-specific `doc_node.value`
    2. direct `doc` attribute
    3. standard library `ast.get_docstring`

    Returns None if no docstring is available or extraction fails.

    Args:
        n: AST node (astroid or standard AST).

    Returns:
        str | None: Extracted docstring or None.
    """
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
    """
    Resolve one step of a dotted matcher attribute path.

    Supports special handling for docstrings, numeric list indexes,
    and regular object attributes.
    """
    if obj is None:
        return None
    if part == "doc":
        return get_doc(obj)
    if part.isdigit():
        idx = int(part)
        return obj[idx] if isinstance(obj, (list, tuple)) and 0 <= idx < len(obj) else None
    return getattr(obj, part, None)


def get_attr(node, dotted):
    """
    Resolve a dotted matcher attribute path from a node.

    Double underscores are treated as path separators. If the final value
    is an astroid Name node, its identifier is returned instead of the node.
    """
    cur = node
    for part in dotted.replace("__", ".").split("."):
        cur = attr_from(cur, part)
        if cur is None:
            break
    if isinstance(cur, anodes.Name):
        return cur.name
    return cur


def resolve_arg_value(matcher, node, attr):
    """
    Resolve a synthetic matcher attribute targeting a call argument.

    This helper interprets attributes such as '__arg_0_name__' or
    '__arg_1_func__' and extracts the requested value from the corresponding
    positional argument of a call-like node.
    """
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


# ===== Call inspection helpers =====
def get_call_name(node):
    """
    Return the simple function name of a call node.

    For example, returns 'print' for `print(x)` and 'append' for `obj.append(x)`.
    """
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
    """
    Return the qualified function path of a call node, if available.

    For example, returns 'os.path.join' for `os.path.join(...)`.
    Simple calls such as `print(...)` return their direct name.
    """
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


# ===== Literal and structural query helpers =====
def is_string_literal(value, *, non_empty: bool = True) -> bool:
    """
    Return True if the value represents a string or bytes literal node.

    Optionally requires the literal to be non-empty after stripping.
    """
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
    """Return True if the subtree contains any node matching the given type selector."""
    allowed = split_types(type_in)
    for n, _depth in walk(matcher, root, max_depth=max_depth):
        if n.__class__.__name__ in allowed:
            return True
    return False


def contains_name(matcher, root, name: str) -> bool:
    """Return True if the subtree contains a name node with the given identifier."""
    if not name:
        return False
    for n, _ in walk(matcher, root):
        if n.__class__.__name__ == "Name":
            ident = getattr(n, "name", None) or getattr(n, "id", None)
            if ident == name:
                return True
    return False


def contains_call_name(matcher, root, names) -> bool:
    """Return True if the subtree contains a call whose simple name matches one of the given names."""
    names = set(names)
    for n, _ in walk(matcher, root):
        if n.__class__.__name__ == "Call":
            nm = get_call_name(n)
            if nm in names:
                return True
    return False


def iter_function_defaults(fn):
    """Return all non-None positional and keyword default values of a function node."""
    args = getattr(fn, "args", None)
    if not args:
        return []
    defaults = getattr(args, "defaults", []) or []
    kw_defaults = getattr(args, "kw_defaults", []) or []
    return [d for d in (defaults + kw_defaults) if d is not None]


# ===== Assignment analysis helpers =====
def get_constant_target_name(node) -> str | None:
    """
    Return the assigned target name for simple constant-like assignments.

    Supports Assign and AnnAssign nodes and returns the first target name when available.
    """
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
    """
    Return a readable target name for an assignment node.

    Supports simple variable assignments as well as attribute assignmentsc such as `obj.attr`.
    """
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
    """Return True if the subtree reads the given identifier via a Name node."""
    for n, _ in walk(matcher, root):
        if n.__class__.__name__ == "Name":
            ident = getattr(n, "name", None) or getattr(n, "id", None)
            if ident == name:
                return True
    return False


def find_previous_overwritten_assign(matcher, node):
    """
    Find an earlier assignment to the same target that is overwritten without being used.

    The search is limited to the same parent block. If the assigned name is read
    between the previous assignment and the current one, no match is returned.
    """
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
    """Return True if the assignment overwrites an earlier unused assignment in the same block."""
    return find_previous_overwritten_assign(matcher, node) is not None


def except_bound_name(node) -> str | None:
    """Return the bound exception variable name from an ExceptHandler node, if present."""
    if node.__class__.__name__ != "ExceptHandler":
        return None

    n = getattr(node, "name", None)
    if not n:
        return None

    if isinstance(n, str):
        return n

    return getattr(n, "name", None) or getattr(n, "id", None)


def test_reason(matcher, node) -> str | None:
    """
    Explain why an If or While condition appears trivially truthy.

    Returns a human-readable reason for simple tautological conditions,
    such as literal truthy values, redundant boolean expressions,
    or self-comparisons like `x == x`.
    """
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


# ===== Value extraction helpers =====
def node_value(n):
    """
    Extract a comparable value representation from a node or literal.

    This helper normalizes constants, names, attributes, and primitive values
    into a simpler form for matcher comparisons.
    """
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
    """
    Collect identifier-like names used within a subtree.

    Includes variable names, accessed attribute names, and callable names
    referenced by call nodes.
    """
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
    """
    Extract a simplified value from common astroid node types.

    Supports constants, names, attributes, and legacy value-like attributes
    such as `value`, `n`, and `s`.
    """
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
