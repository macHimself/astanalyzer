"""
Utility helpers used by style, structure, and fix-related rules.

This module provides small reusable functions for:
- naming convention checks
- empty block and redundant control-flow detection
- return-count and line-length analysis
- whitespace and formatting helpers
- small predicate factories used in matcher conditions

Most helpers are intended for internal rule implementation rather than
direct public use.
"""

from __future__ import annotations

import re
from typing import Iterable, Tuple, List

#: Compiled regex for snake_case identifiers.
#: Pattern: lowercase letters, digits and underscores,
#: must start with a lowercase letter or underscore.
SNAKE = re.compile(r'^[a-z_][a-z0-9_]*$')

#: Compiled regex for PascalCase (PASCALCase starting uppercase).
#: Pattern: must start with uppercase letter,
#: followed by alphanumeric characters only.
PASCAL = re.compile(r'^[A-Z][a-zA-Z0-9]*$')

BLOCK_TYPES = ("If", "For", "While", "Try", "With", "ExceptHandler")

TERMINAL = {"Return", "Raise", "Break", "Continue"}

STOP_TYPES = {"FunctionDef", "AsyncFunctionDef", "ClassDef"}

_TRAIL_RE = re.compile(r"[ \t]+$")


# ===== Naming helpers =====
def is_snake(name: str) -> bool:
    """Return True if `name` follows snake_case convention.

    Args:
        name: Identifier string to validate.

    Returns:
        True if the name matches the snake_case regex, otherwise False.

    Notes:
        This is a purely syntactic check and does not validate reserved words
        or semantic correctness.
    """
    return bool(SNAKE.match(name))


def is_pascal(name: str) -> bool:
    """Return True if `name` follows PascalCase convention.

    Args:
        name: Identifier string to validate.

    Returns:
        True if the name matches the PascalCase regex, otherwise False.

    Notes:
        This function checks for leading uppercase character. It does not
        distinguish between PASCALCase and PascalCase variants beyond that.
    """
    return bool(PASCAL.match(name))


# ===== Assignment / usage helpers =====
def is_unused_assign(node) -> bool:
    """Return True if a simple assignment target is not referenced later in the same block."""
    targets = getattr(node, "targets", None)
    if not targets or len(targets) != 1:
        return False

    name = getattr(targets[0], "name", None)
    if not name:
        return False

    parent = getattr(node, "parent", None)
    body = getattr(parent, "body", None)
    if not isinstance(body, list):
        return False

    for stmt in body:
        if stmt is node:
            continue
        if name in getattr(stmt, "as_string", lambda: "")():
            return False

    return True


# ===== Loop and comprehension helpers =====
def loop_comprehension_suggestion(for_node):
    """
    Suggest a list, set, or dict comprehension replacement for a simple loop.

    Returns:
        tuple[str | None, str | None]:
            Pair of (kind, suggestion), or (None, None) if no safe rewrite pattern is found.
    """
    def s(n): return (getattr(n, "as_string", None) or (lambda: ""))()

    # prev sibling
    p = getattr(for_node, "parent", None)
    if not p or not hasattr(p, "body"):
        return (None, None)
    body = list(p.body)
    try:
        i = body.index(for_node)
    except ValueError:
        return (None, None)
    prev = body[i - 1] if i > 0 else None
    if not prev or prev.__class__.__name__ != "Assign":
        return (None, None)

    # acc init
    t0 = (getattr(prev, "targets", None) or [None])[0]
    acc = getattr(t0, "id", None) or getattr(t0, "name", None)
    v = getattr(prev, "value", None)
    if not acc or not v:
        return (None, None)

    kind = None
    vc = v.__class__.__name__
    if vc == "List": kind = "list"
    elif vc == "Dict": kind = "dict"
    elif vc == "Call":
        fn = getattr(getattr(v, "func", None), "name", None) or getattr(getattr(v, "func", None), "id", None)
        if fn in ("list", "set", "dict"):
            kind = "set" if fn == "set" else fn
    if not kind:
        return (None, None)

    # loop body must be: [Expr(Call(acc.append/add(...)))] or Assign(acc[key]=val)
    b = getattr(for_node, "body", []) or []
    if not b:
        return (None, None)

    stmt = b[0]
    cond = None
    if stmt.__class__.__name__ == "If":
        cond = s(getattr(stmt, "test", None))
        stmt = (getattr(stmt, "body", []) or [None])[0]
        if stmt is None:
            return (None, None)
    elif len(b) > 1:
        return (None, None)

    target = s(getattr(for_node, "target", None)) or "_"
    it = s(getattr(for_node, "iter", None)) or "iterable"

    if kind in ("list", "set"):
        if stmt.__class__.__name__ != "Expr":
            return (None, None)
        call = getattr(stmt, "value", None)
        if not call or call.__class__.__name__ != "Call":
            return (None, None)
        f = getattr(call, "func", None)
        if not f or f.__class__.__name__ != "Attribute":
            return (None, None)
        base = getattr(f, "expr", None) or getattr(f, "value", None)
        base_name = getattr(base, "name", None) or getattr(base, "id", None)
        meth = getattr(f, "attrname", None) or getattr(f, "attr", None) or getattr(f, "name", None)
        if base_name != acc:
            return (None, None)

        want = "append" if kind == "list" else "add"
        if meth != want:
            return (None, None)

        args = getattr(call, "args", []) or []
        if not args:
            return (None, None)
        e = s(args[0])
        if not e:
            return (None, None)

        if kind == "list":
            sug = f"{acc} = [{e} for {target} in {it}{(' if ' + cond) if cond else ''}]"
            return ("list", sug)
        else:
            sug = f"{acc} = {{{e} for {target} in {it}{(' if ' + cond) if cond else ''}}}"
            return ("set", sug)

    if kind == "dict":
        if stmt.__class__.__name__ != "Assign":
            return (None, None)
        t0 = (getattr(stmt, "targets", None) or [None])[0]
        if not t0 or t0.__class__.__name__ != "Subscript":
            return (None, None)
        base = getattr(t0, "value", None) or getattr(t0, "expr", None)
        base_name = getattr(base, "name", None) or getattr(base, "id", None)
        if base_name != acc:
            return (None, None)
        key = getattr(t0, "slice", None) or getattr(t0, "index", None)
        k = s(key)
        val = s(getattr(stmt, "value", None))
        if not k or not val:
            return (None, None)
        sug = f"{acc} = {{{k}: {val} for {target} in {it}{(' if ' + cond) if cond else ''}}}"
        return ("dict", sug)

    return (None, None)


def is_loop_comprehension_candidate(for_node) -> bool:
    """Return True if the loop can be rewritten as a comprehension."""
    kind, sug = loop_comprehension_suggestion(for_node)
    return bool(kind and sug)


# ===== Empty block helpers =====
def is_noop_stmt(stmt) -> bool:
    """Return True if the statement is effectively a no-op, such as pass or a docstring-only expression."""
    if stmt.__class__.__name__ == "Pass":
        return True
    if stmt.__class__.__name__ == "Expr":
        v = getattr(stmt, "value", None)
        val = getattr(v, "value", None)
        return isinstance(val, str)

    return False


def is_empty_seq(seq) -> bool:
    """Return True if the sequence is empty or contains only no-op statements."""
    if not seq:
        return True
    return all(is_noop_stmt(s) for s in seq)


def iter_relevant_bodies(node) -> Iterable[Tuple[str, list]]:
    """
    Yield named statement bodies relevant for empty-block analysis.

    Examples include `body`, `orelse`, exception handler bodies, and `finalbody`.
    """
    if hasattr(node, "body"):
        yield ("body", getattr(node, "body") or [])

    t = node.__class__.__name__

    if t == "If":
        yield ("orelse", getattr(node, "orelse") or [])

    if t == "Try":
        handlers = getattr(node, "handlers", []) or []
        for i, h in enumerate(handlers):
            yield (f"handler[{i}]", getattr(h, "body", []) or [])
        yield ("finalbody", getattr(node, "finalbody", []) or [])


def is_empty_block(node) -> bool:
    """Return True if any relevant body of the node is empty or contains only no-op statements."""
    if node.__class__.__name__ not in BLOCK_TYPES:
        return False
    for _, seq in iter_relevant_bodies(node):
        if is_empty_seq(seq):
            return True
    return False


def empty_parts(node) -> List[str]:
    """Return names of block parts that are empty or contain only no-op statements."""
    parts: List[str] = []
    for name, seq in iter_relevant_bodies(node):
        if is_empty_seq(seq):
            parts.append(name)
    return parts


# ===== Control-flow helpers =====
def is_terminal_stmt(stmt) -> bool:
    return stmt.__class__.__name__ in TERMINAL


def body_ends_terminal(seq) -> bool:
    seq = seq or []
    return bool(seq) and is_terminal_stmt(seq[-1])


def has_redundant_else_after_terminal(node) -> bool:
    """
    Return True if an if/elif/else chain contains an unnecessary else branch
    after a terminal statement.
    """
    if node.__class__.__name__ != "If":
        return False

    orelse = getattr(node, "orelse", []) or []
    if not orelse:
        return False

    if orelse[0].__class__.__name__ != "If":
        return body_ends_terminal(getattr(node, "body", []) or [])

    cur = node
    while True:
        if not body_ends_terminal(getattr(cur, "body", []) or []):
            return False

        tail = getattr(cur, "orelse", []) or []
        if not tail:
            return False

        if tail[0].__class__.__name__ != "If":
            return True

        cur = tail[0]


def count_returns_in_function(node, *, stop_after: int | None = None) -> int:
    """
    Count return statements inside a function while ignoring nested scopes.

    Nested functions and classes are not traversed.
    """
    if node.__class__.__name__ not in {"FunctionDef", "AsyncFunctionDef"}:
        return 0

    count = 0
    seen = set()
    stack = [node]

    while stack:
        cur = stack.pop()
        oid = id(cur)
        if oid in seen:
            continue
        seen.add(oid)

        typ = cur.__class__.__name__
        if typ == "Return":
            count += 1
            if stop_after is not None and count >= stop_after:
                return count

        if typ in STOP_TYPES and cur is not node:
            continue

        for ch in cur.get_children():
            stack.append(ch)

    return count


def has_multiple_returns(node) -> bool:
    """Return True if the function contains at least two return statements."""
    return count_returns_in_function(node, stop_after=2) >= 2


# ===== File content and line helpers =====
def get_file_content_from_node(node) -> str | None:
    """Return cached source file content from the node root, if available."""
    root = node.root() if hasattr(node, "root") else None
    return getattr(root, "file_content", None)


def long_line_numbers(node, max_len: int) -> list[int]:
    """Return source line numbers whose length exceeds the given limit."""
    content = get_file_content_from_node(node)
    if not content:
        return []
    nums = []
    for i, line in enumerate(content.splitlines(), start=1):
        if len(line.rstrip("\n")) > max_len:
            nums.append(i)
    return nums


def has_long_lines(node, max_len: int) -> bool:
    """Return True if the source file contains any line longer than the given limit."""
    return bool(long_line_numbers(node, max_len))


# ===== Constant and whitespace helpers =====
def is_module_constant(node) -> bool:
    """
    Return True if the node represents a simple module-level constant assignment.

    Dunder names are excluded.
    """
    parent = getattr(node, "parent", None)
    if not parent or parent.__class__.__name__ != "Module":
        return False
    
    if node.__class__.__name__ == "Assign":
        targets = getattr(node, "targets", []) or []
        if not targets:
            return False
        name = getattr(targets[0], "name", None) or getattr(targets[0], "id", None)
    elif node.__class__.__name__ == "AnnAssign":
        t = getattr(node, "target", None)
        name = getattr(t, "name", None) or getattr(t, "id", None)
    else:
        return False

    if not name:
        return False

    if name.startswith("__") and name.endswith("__"):
        return False

    value = getattr(node, "value", None)
    if value is None:
        return False

    return value.__class__.__name__ in (
        "Const", "Constant", "Num", "Str", "Bytes",
        "Tuple", "List", "Set", "Dict"
    )


def has_trailing_whitespace(module_node) -> bool:
    """Return True if the module source contains trailing whitespace."""
    content = getattr(module_node.root(), "file_content", None)
    if not content:
        return False
    return any(_TRAIL_RE.search(line) for line in content.splitlines())


def trailing_whitespace_comment(module_node) -> str:
    """Build a human-readable comment describing lines with trailing whitespace."""
    content = getattr(module_node.root(), "file_content", None) or ""
    lines = content.splitlines()
    hits = [str(i) for i, line in enumerate(lines, 1) if _TRAIL_RE.search(line)]
    if not hits:
        return "# No trailing whitespace found."
    preview = ", ".join(hits[:15]) + (" ..." if len(hits) > 15 else "")
    return f"# Trailing whitespace detected on lines: {preview}. Remove spaces/tabs at EOL."


def strip_trailing_whitespace(module_node, suggestion_lines, context, **kwargs):
    """
    Rewrite suggestion lines with trailing spaces and tabs removed from line ends.
    """
    content = getattr(module_node.root(), "file_content", None)
    if not content:
        return
    fixed = "\n".join(_TRAIL_RE.sub("", line) for line in content.splitlines())
    context["original"][0] = content
    suggestion_lines[:] = fixed.splitlines()


# ===== Definition spacing and docstring insertion helpers =====
def missing_blank_before_def(node) -> bool:
    """Return True if the definition is missing the required blank lines before it."""
    parent = getattr(node, "parent", None)
    if parent is None or not hasattr(parent, "body"):
        return False

    body = list(parent.body)
    try:
        idx = body.index(node)
    except ValueError:
        return False
    if idx == 0:
        return False

    prev = body[idx - 1]
    content = getattr(node.root(), "file_content", None)
    if not content:
        return False

    required = 1 if getattr(parent, "__class__", None).__name__ == "ClassDef" else 2

    prev_end = getattr(prev, "end_lineno", getattr(prev, "lineno", 0))
    cur_line = getattr(node, "lineno", 0)
    if cur_line <= prev_end + 1:
        blanks = 0
    else:
        lines = content.splitlines()
        lo = max(1, prev_end + 1)
        hi = min(len(lines), cur_line - 1)
        blanks = 0
        for i in range(lo, hi + 1):
            if lines[i - 1].strip() == "":
                blanks += 1

    return blanks < required


def missing_blank_before_def_comment(node) -> str:
    """Return an explanatory comment for a missing blank line before a definition."""
    parent = getattr(node, "parent", None)
    required = 1 if getattr(parent, "__class__", None).__name__ == "ClassDef" else 2
    return f"# Missing blank line(s) before this definition (PEP 8: require {required} here)."


def insert_function_docstring(node, suggestion_lines, context, **kwargs):
    """Insert a generated docstring into a function definition suggestion."""
    text = kwargs.get("text") or '"""TODO: Describe the function."""'
    if not suggestion_lines:
        return

    indent = " " * (getattr(node, "col_offset", 0) + 4)
    sig = suggestion_lines[0]
    if ":" in sig and sig.strip().endswith(":") is False:
        before, after = sig.split(":", 1)
        suggestion_lines[0] = f"{before}:"
        suggestion_lines.insert(1, f"{indent}{text}")
        rest = after.strip()
        if rest:
            suggestion_lines.insert(2, f"{indent}{rest}")
        return

    suggestion_lines.insert(1, f"{indent}{text}")


def insert_class_docstring(node, suggestion_lines, context, **kwargs):
    """Insert a generated docstring into a class definition suggestion."""
    text = kwargs.get("text") or '"""TODO: Describe the class purpose, attributes, and usage."""'
    if not suggestion_lines:
        return
    
    indent = " " * (getattr(node, "col_offset", 0) + 4)
    sig = suggestion_lines[0]
    if ":" in sig and not sig.strip().endswith(":"):
        before, after = sig.split(":", 1)
        suggestion_lines[0] = f"{before}:"
        suggestion_lines.insert(1, f"{indent}{text}")
        rest = after.strip()
        if rest:
            suggestion_lines.insert(2, f"{indent}{rest}")
        return
    
    suggestion_lines.insert(1, f"{indent}{text}")


# ===== Compare helpers =====
def _is_none_const(n) -> bool:
    """Return True if the node represents the literal value None."""
    return (
        n is not None
        and n.__class__.__name__ in ("Const", "Constant", "NameConstant")
        and getattr(n, "value", "___") is None
    )


def _iter_compare_pairs(node):
    """
    Yield normalized comparison pairs from a Compare node.

    Each yielded item is `(operator_name, left, right)`.
    Supports both astroid-style and tuple-based comparison representations.
    """
    if node.__class__.__name__ != "Compare":
        return

    left = getattr(node, "left", None)
    ops = getattr(node, "ops", []) or []
    comparators = getattr(node, "comparators", None)

    if comparators is not None:
        prev = left
        for i, op in enumerate(ops):
            if i >= len(comparators):
                break
            op_name = getattr(op, "__class__", type("X", (), {})).__name__
            yield (op_name, prev, comparators[i])
            prev = comparators[i]
        return

    prev = left
    for item in ops:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue

        op_raw, right = item
        if isinstance(op_raw, str):
            op_map = {
                "==": "Eq",
                "!=": "NotEq",
                "is": "Is",
                "is not": "IsNot",
                "<": "Lt",
                "<=": "LtE",
                ">": "Gt",
                ">=": "GtE",
                "in": "In",
                "not in": "NotIn",
            }
            op_name = op_map.get(op_raw, op_raw)
        else:
            op_name = getattr(op_raw, "__class__", type("X", (), {})).__name__

        yield (op_name, prev, right)
        prev = right


# ===== Predicate factory helpers =====
def function_arg_count(node) -> int:
    """Return the number of positional-only, positional, and keyword-only arguments of a function node."""
    args = getattr(node, "args", None)
    if args is None:
        return 0

    posonly = len(getattr(args, "posonlyargs", []) or [])
    normal = len(getattr(args, "args", []) or [])
    kwonly = len(getattr(args, "kwonlyargs", []) or [])

    return posonly + normal + kwonly


def arg_count_gt(limit: int):
    """
    Build a predicate that matches functions with more than `limit` arguments.
    """
    def _check(node) -> bool:
        if node.__class__.__name__ not in {"FunctionDef", "AsyncFunctionDef"}:
            return False
        return function_arg_count(node) > limit
    return _check


def parent_depth_at_least(type_names: tuple[str, ...], min_depth: int):
    """
    Build a predicate that matches nodes nested inside the given parent types
    at least `min_depth` times.
    """
    allowed = set(type_names)

    def _check(node) -> bool:
        depth = 0
        parent = getattr(node, "parent", None)

        while parent is not None:
            if parent.__class__.__name__ in allowed:
                depth += 1
            parent = getattr(parent, "parent", None)

        return depth >= min_depth

    return _check
