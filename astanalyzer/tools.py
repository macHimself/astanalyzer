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
    if for_node.__class__.__name__ != "For":
        return (None, None)

    parent = getattr(for_node, "parent", None)
    if not parent or not hasattr(parent, "body"):
        return (None, None)

    parent_body = list(getattr(parent, "body", []) or [])
    try:
        index = parent_body.index(for_node)
    except ValueError:
        return (None, None)

    prev_stmt = parent_body[index - 1] if index > 0 else None
    if prev_stmt is None or prev_stmt.__class__.__name__ != "Assign":
        return (None, None)

    prev_targets = getattr(prev_stmt, "targets", None) or []
    if len(prev_targets) != 1:
        return (None, None)

    acc_target = prev_targets[0]
    acc_name = getattr(acc_target, "id", None) or getattr(acc_target, "name", None)
    if not acc_name:
        return (None, None)

    init_value = getattr(prev_stmt, "value", None)
    kind = _infer_comprehension_accumulator_kind(init_value)
    if not kind:
        return (None, None)

    loop_body = getattr(for_node, "body", None) or []
    if len(loop_body) != 1:
        return (None, None)

    stmt = loop_body[0]
    condition_text = None

    if stmt.__class__.__name__ == "If":
        # Filtered comprehension is OK only when there is no else branch.
        if getattr(stmt, "orelse", None):
            return (None, None)

        if_body = getattr(stmt, "body", None) or []
        if len(if_body) != 1:
            return (None, None)

        condition_text = _node_text(getattr(stmt, "test", None))
        if not condition_text:
            return (None, None)

        stmt = if_body[0]

    extracted = _extract_single_collection_build_stmt(stmt, acc_name)
    if not extracted:
        return (None, None)

    target_text = _node_text(getattr(for_node, "target", None)) or "_"
    iter_text = _node_text(getattr(for_node, "iter", None)) or "iterable"
    suffix = f" if {condition_text}" if condition_text else ""

    if extracted[0] == "list" and kind == "list":
        expr_text = extracted[1]
        suggestion = f"{acc_name} = [{expr_text} for {target_text} in {iter_text}{suffix}]"
        return ("list", suggestion)

    if extracted[0] == "set" and kind == "set":
        expr_text = extracted[1]
        suggestion = f"{acc_name} = {{{expr_text} for {target_text} in {iter_text}{suffix}}}"
        return ("set", suggestion)

    if extracted[0] == "dict" and kind == "dict":
        key_text, value_text = extracted[1], extracted[2]
        suggestion = f"{acc_name} = {{{key_text}: {value_text} for {target_text} in {iter_text}{suffix}}}"
        return ("dict", suggestion)

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
def function_arg_count(
    node,
    *,
    ignore_bound_first_arg: bool = True,
    ignore_init: bool = False,
) -> int:
    """Return the number of relevant function arguments for complexity checks."""
    args = getattr(node, "args", None)
    if args is None:
        return 0

    if ignore_init and getattr(node, "name", None) == "__init__":
        return 0

    posonly_args = list(getattr(args, "posonlyargs", []) or [])
    normal_args = list(getattr(args, "args", []) or [])
    kwonly_args = list(getattr(args, "kwonlyargs", []) or [])

    count = len(posonly_args) + len(normal_args) + len(kwonly_args)

    if ignore_bound_first_arg and normal_args:
        first_name = getattr(normal_args[0], "name", None)
        if first_name in {"self", "cls"}:
            count -= 1

    return max(count, 0)


def arg_count_gt(
    limit: int,
    *,
    ignore_bound_first_arg: bool = True,
    ignore_init: bool = False,
):
    """Build a predicate that matches functions with more than `limit` relevant arguments."""
    def _check(node) -> bool:
        if node.__class__.__name__ not in {"FunctionDef", "AsyncFunctionDef"}:
            return False
        return function_arg_count(
            node,
            ignore_bound_first_arg=ignore_bound_first_arg,
            ignore_init=ignore_init,
        ) > limit
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


def count_relevant_statements(node) -> int:
    """
    Count executable statements in a function while ignoring no-op string
    expressions and nested function/class scopes.
    """
    def _count_stmt(stmt) -> int:
        if is_noop_stmt(stmt):
            return 0

        t = stmt.__class__.__name__
        if t in {"FunctionDef", "AsyncFunctionDef", "ClassDef"}:
            return 0

        total = 1

        for attr in ("body", "orelse", "finalbody"):
            seq = getattr(stmt, attr, None)
            if isinstance(seq, list):
                total += sum(_count_stmt(s) for s in seq)

        handlers = getattr(stmt, "handlers", None) or []
        for h in handlers:
            total += sum(_count_stmt(s) for s in (getattr(h, "body", None) or []))

        return total

    body = getattr(node, "body", None) or []
    return sum(_count_stmt(stmt) for stmt in body)


def _iter_scope_locals(scope_node):
    """Yield names defined directly in the given scope."""
    body = getattr(scope_node, "body", None) or []
    for stmt in body:
        t = stmt.__class__.__name__

        if t in {"FunctionDef", "AsyncFunctionDef", "ClassDef"}:
            yield getattr(stmt, "name", None)

        elif t in {"Assign", "AnnAssign"}:
            targets = getattr(stmt, "targets", None) or []
            if t == "AnnAssign":
                target = getattr(stmt, "target", None)
                if target is not None:
                    targets = [target]
            for target in targets:
                name = getattr(target, "name", None) or getattr(target, "id", None)
                if name:
                    yield name

        elif t in {"Import", "ImportFrom"}:
            for alias in getattr(stmt, "names", []) or []:
                if isinstance(alias, tuple):
                    original, asname = alias
                    yield asname or original.split(".")[0]


def get_enclosing_scope(node):
    cur = getattr(node, "parent", None)
    while cur is not None:
        if cur.__class__.__name__ in {"FunctionDef", "AsyncFunctionDef", "Module", "Lambda"}:
            return cur
        cur = getattr(cur, "parent", None)
    return None


def is_name_shadowed_in_scope(node, name: str) -> bool:
    """Return True if `name` is defined in the enclosing lexical scope."""
    scope = get_enclosing_scope(node)
    if scope is None:
        return False

    # function params
    if scope.__class__.__name__ in {"FunctionDef", "AsyncFunctionDef", "Lambda"}:
        args = getattr(scope, "args", None)
        if args is not None:
            for seq_name in ("posonlyargs", "args", "kwonlyargs"):
                for arg in getattr(args, seq_name, []) or []:
                    if getattr(arg, "name", None) == name:
                        return True
            vararg = getattr(args, "vararg", None)
            kwarg = getattr(args, "kwarg", None)
            if getattr(vararg, "name", None) == name:
                return True
            if getattr(kwarg, "name", None) == name:
                return True

    return name in set(filter(None, _iter_scope_locals(scope)))


def is_builtin_print_call(node) -> bool:
    if node.__class__.__name__ != "Call":
        return False

    func = getattr(node, "func", None)
    if func is None or func.__class__.__name__ != "Name":
        return False

    called = getattr(func, "name", None) or getattr(func, "id", None)
    if called != "print":
        return False

    return not is_name_shadowed_in_scope(node, "print")


def is_builtin_name_call(node, allowed_names) -> bool:
    if node.__class__.__name__ != "Call":
        return False

    func = getattr(node, "func", None)
    if func is None or func.__class__.__name__ != "Name":
        return False

    called = getattr(func, "name", None) or getattr(func, "id", None)
    if called not in set(allowed_names):
        return False

    return not is_name_shadowed_in_scope(node, called)


def is_redundant_sorted_before_minmax(node) -> bool:
    if not is_builtin_name_call(node, {"min", "max"}):
        return False

    args = getattr(node, "args", []) or []
    if len(args) != 1:
        return False

    inner = args[0]
    if inner.__class__.__name__ != "Call":
        return False

    return is_builtin_name_call(inner, {"sorted"})


def is_probably_str_join_call(node) -> bool:
    if node.__class__.__name__ != "Call":
        return False

    func = getattr(node, "func", None)
    if func is None:
        return False

    # reject plain join(...)
    if func.__class__.__name__ == "Name":
        called = getattr(func, "name", None) or getattr(func, "id", None)
        if called == "join":
            return False
        return False

    # accept only "<string-literal>.join(...)"
    if func.__class__.__name__ != "Attribute":
        return False

    base = getattr(func, "expr", None) or getattr(func, "value", None)
    if base is None:
        return False

    base_value = getattr(base, "value", None)
    attr = getattr(func, "attrname", None) or getattr(func, "attr", None) or getattr(func, "name", None)

    return attr == "join" and isinstance(base_value, str)


def _assigned_names_in_body(body) -> set[str]:
    names = set()
    for stmt in body or []:
        t = stmt.__class__.__name__
        if t in {"Assign", "AnnAssign"}:
            targets = getattr(stmt, "targets", None) or []
            if t == "AnnAssign":
                target = getattr(stmt, "target", None)
                if target is not None:
                    targets = [target]
            for target in targets:
                name = getattr(target, "name", None) or getattr(target, "id", None)
                if name:
                    names.add(name)
    return names


def is_nested_loop_same_stable_collection(node) -> bool:
    if node.__class__.__name__ != "For":
        return False

    outer = getattr(node, "parent", None)
    while outer is not None and outer.__class__.__name__ != "For":
        outer = getattr(outer, "parent", None)

    if outer is None:
        return False

    inner_iter = getattr(node, "iter", None)
    outer_iter = getattr(outer, "iter", None)
    if inner_iter is None or outer_iter is None:
        return False

    # reject calls like get_items() vs get_items()
    if inner_iter.__class__.__name__ == "Call" or outer_iter.__class__.__name__ == "Call":
        return False

    inner_text = getattr(inner_iter, "as_string", lambda: "")()
    outer_text = getattr(outer_iter, "as_string", lambda: "")()
    if inner_text != outer_text:
        return False

    # if the iterable name is reassigned inside outer body before inner loop, reject
    if inner_iter.__class__.__name__ == "Name":
        iter_name = getattr(inner_iter, "name", None) or getattr(inner_iter, "id", None)
        outer_body = getattr(outer, "body", []) or []
        seen_inner = False
        for stmt in outer_body:
            if stmt is node:
                seen_inner = True
                break
            if iter_name in _assigned_names_in_body([stmt]):
                return False

    return True


def _node_text(node) -> str:
    """Return a stable string form of an AST node, or empty string."""
    return (getattr(node, "as_string", None) or (lambda: ""))()


def _infer_comprehension_accumulator_kind(init_value) -> str | None:
    """
    Infer whether the accumulator initialization corresponds to a list, set, or dict.

    Supported forms:
        result = []
        result = {}
        result = list()
        result = set()
        result = dict()
    """
    if init_value is None:
        return None

    value_type = init_value.__class__.__name__

    if value_type == "List":
        return "list"

    if value_type == "Dict":
        return "dict"

    if value_type == "Call":
        func = getattr(init_value, "func", None)
        func_name = getattr(func, "name", None) or getattr(func, "id", None)
        if func_name in {"list", "set", "dict"}:
            return func_name

    return None


def _extract_single_collection_build_stmt(stmt, acc_name: str):
    """
    Extract a simple collection-building statement suitable for comprehension rewriting.

    Supported patterns:
        acc.append(expr)
        acc.add(expr)
        acc[key] = value

    Returns:
        tuple[str, ...] | None

    Shapes:
        ("list", expr_text)
        ("set", expr_text)
        ("dict", key_text, value_text)
    """
    stmt_type = stmt.__class__.__name__

    if stmt_type == "Expr":
        call = getattr(stmt, "value", None)
        if call is None or call.__class__.__name__ != "Call":
            return None

        func = getattr(call, "func", None)
        if func is None or func.__class__.__name__ != "Attribute":
            return None

        base = getattr(func, "expr", None) or getattr(func, "value", None)
        base_name = getattr(base, "name", None) or getattr(base, "id", None)
        method_name = (
            getattr(func, "attrname", None)
            or getattr(func, "attr", None)
            or getattr(func, "name", None)
        )

        if base_name != acc_name:
            return None

        args = getattr(call, "args", []) or []
        if len(args) != 1:
            return None

        expr_text = _node_text(args[0])
        if not expr_text:
            return None

        if method_name == "append":
            return ("list", expr_text)

        if method_name == "add":
            return ("set", expr_text)

        return None

    if stmt_type == "Assign":
        targets = getattr(stmt, "targets", None) or []
        if len(targets) != 1:
            return None

        target = targets[0]
        if target.__class__.__name__ != "Subscript":
            return None

        base = getattr(target, "value", None) or getattr(target, "expr", None)
        base_name = getattr(base, "name", None) or getattr(base, "id", None)
        if base_name != acc_name:
            return None

        key_node = getattr(target, "slice", None) or getattr(target, "index", None)
        key_text = _node_text(key_node)
        value_text = _node_text(getattr(stmt, "value", None))

        if not key_text or not value_text:
            return None

        return ("dict", key_text, value_text)

    return None