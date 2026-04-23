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
from collections.abc import Iterable


#: Compiled regex for snake_case identifiers.
#: Pattern: lowercase letters, digits and underscores,
#: must start with a lowercase letter or underscore.
SNAKE = re.compile(r"^[a-z_][a-z0-9_]*$")

#: Compiled regex for PascalCase.
#: Pattern: must start with uppercase letter,
#: followed by alphanumeric characters only.
PASCAL = re.compile(r"^[A-Z][a-zA-Z0-9]*$")

BLOCK_TYPES = ("If", "For", "While", "Try", "With", "ExceptHandler")
TERMINAL = {"Return", "Raise", "Break", "Continue"}
STOP_TYPES = {"FunctionDef", "AsyncFunctionDef", "ClassDef"}

_TRAIL_RE = re.compile(r"[ \t]+$")


# ===== Generic AST helpers =====
def _node_type(node) -> str:
    """Return AST node class name, or empty string for None."""
    return node.__class__.__name__ if node is not None else ""


def _node_name(node) -> str | None:
    """Return a best-effort identifier name from a node."""
    if node is None:
        return None
    return getattr(node, "name", None) or getattr(node, "id", None)


def _attr_name(node) -> str | None:
    """Return a best-effort attribute name from an attribute-like node."""
    if node is None:
        return None
    return (
        getattr(node, "attrname", None)
        or getattr(node, "attr", None)
        or getattr(node, "name", None)
    )


def _node_text(node) -> str:
    """Return a stable string form of an AST node, or empty string."""
    return (getattr(node, "as_string", None) or (lambda: ""))()


def _assignment_targets(node) -> list:
    """Return assignment targets normalized for Assign and AnnAssign nodes."""
    node_type = _node_type(node)

    if node_type == "Assign":
        return list(getattr(node, "targets", []) or [])

    if node_type == "AnnAssign":
        target = getattr(node, "target", None)
        return [target] if target is not None else []

    return []


# ===== Naming helpers =====
def is_snake(name: str) -> bool:
    """Return True if `name` follows snake_case convention."""
    return bool(SNAKE.match(name))


def is_pascal(name: str) -> bool:
    """Return True if `name` follows PascalCase convention."""
    return bool(PASCAL.match(name))


def split_identifier_parts(name: str) -> list[str]:
    """
    Split identifier into semantic parts using underscores and camel-case boundaries.

    Examples:
        api_key -> ["api", "key"]
        apiKey -> ["api", "key"]
        accessToken -> ["access", "token"]
        monkey -> ["monkey"]
    """
    if not name:
        return []

    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return [part.lower() for part in normalized.split("_") if part]


# ===== Assignment / usage helpers =====
def _flatten_target_names(target) -> list[str]:
    """Extract all simple assigned names from a target, including tuple/list unpacking."""
    target_type = _node_type(target)

    if target_type in {"AssignName", "Name"}:
        name = _node_name(target)
        return [name] if name else []

    if target_type in {"Tuple", "List"}:
        names: list[str] = []
        for child in getattr(target, "elts", []) or []:
            names.extend(_flatten_target_names(child))
        return names

    return []


def _assignment_target_names(node) -> list[str]:
    """Return all simple names assigned by an Assign/AnnAssign node."""
    names: list[str] = []
    for target in _assignment_targets(node):
        names.extend(_flatten_target_names(target))
    return names


def _text_uses_name(node, name: str) -> bool:
    """Return True if node text references the given name as a whole identifier."""
    text = _node_text(node)
    if not text:
        return False
    return re.search(rf"\b{re.escape(name)}\b", text) is not None


def _stmt_assigns_name(stmt, name: str) -> bool:
    """Return True if the statement assigns to the given name."""
    if _node_type(stmt) not in {"Assign", "AnnAssign"}:
        return False
    return name in _assignment_target_names(stmt)


def _stmt_reads_name_before_overwrite(stmt, name: str) -> bool:
    """
    Return True if the statement reads `name` before overwriting it.

    This is a heuristic ordering helper for common control-flow statements.
    """
    stmt_type = _node_type(stmt)

    if stmt_type == "If":
        test = getattr(stmt, "test", None)
        if _text_uses_name(test, name):
            return True

        for child in getattr(stmt, "body", None) or []:
            if _stmt_reads_name_before_overwrite(child, name):
                return True
            if _stmt_assigns_name(child, name):
                break

        for child in getattr(stmt, "orelse", None) or []:
            if _stmt_reads_name_before_overwrite(child, name):
                return True
            if _stmt_assigns_name(child, name):
                break

        return False

    if stmt_type == "While":
        test = getattr(stmt, "test", None)
        if _text_uses_name(test, name):
            return True

        for child in getattr(stmt, "body", None) or []:
            if _stmt_reads_name_before_overwrite(child, name):
                return True
            if _stmt_assigns_name(child, name):
                break

        for child in getattr(stmt, "orelse", None) or []:
            if _stmt_reads_name_before_overwrite(child, name):
                return True
            if _stmt_assigns_name(child, name):
                break

        return False

    if stmt_type in {"Assign", "AnnAssign"}:
        value = getattr(stmt, "value", None)
        return _text_uses_name(value, name)

    return _text_uses_name(stmt, name)


def is_local_function_assignment(node) -> bool:
    """
    Return True if the assignment is inside a function-like local scope.

    Dead-code heuristics for assignments are reliable mainly for local variables,
    not for module-level or class-level declarations that may be used elsewhere.
    """
    parent = getattr(node, "parent", None)
    while parent is not None:
        parent_type = _node_type(parent)

        if parent_type in {"FunctionDef", "AsyncFunctionDef", "Lambda"}:
            return True

        if parent_type in {"ClassDef", "Module"}:
            return False

        parent = getattr(parent, "parent", None)

    return False


def _enclosing_control_flow_statement(node):
    """
    Return the nearest enclosing control-flow statement that owns the current
    statement via one of its statement-list attributes.
    """
    cur = node
    parent = getattr(cur, "parent", None)

    while parent is not None:
        parent_type = _node_type(parent)
        if parent_type in {"If", "For", "While", "Try", "With", "ExceptHandler"}:
            for attr in ("body", "orelse", "finalbody"):
                seq = getattr(parent, attr, None)
                if isinstance(seq, list) and cur in seq:
                    return parent

        cur = parent
        parent = getattr(cur, "parent", None)

    return None


def _iter_following_statement_groups_after_control_flow(node):
    """
    Yield following statement groups after enclosing control-flow statements.

    This is used for assignments inside branches or loops that may be read later
    after the enclosing block completes.
    """
    cur = node
    seen: set[int] = set()

    while True:
        control = _enclosing_control_flow_statement(cur)
        if control is None:
            return

        oid = id(control)
        if oid in seen:
            return
        seen.add(oid)

        parent = getattr(control, "parent", None)
        if parent is None:
            return

        for attr in ("body", "orelse", "finalbody"):
            seq = getattr(parent, attr, None)
            if isinstance(seq, list) and control in seq:
                idx = seq.index(control)
                following = seq[idx + 1:]
                if following:
                    yield following
                break

        cur = control


def _is_name_read_after_enclosing_control_flow(node, name: str) -> bool:
    """Return True if name is read after one of the enclosing control-flow blocks finishes."""
    for statements in _iter_following_statement_groups_after_control_flow(node):
        for stmt in statements:
            if _stmt_reads_name_before_overwrite(stmt, name):
                return True
    return False


def _is_name_used_by_enclosing_while_next_iteration(node, name: str) -> bool:
    """
    Return True if `name` is assigned inside a while-body and then used
    by the enclosing while on the next iteration.

    This covers:
    - use in the while test itself
    - use in statements that appear before the current assignment within the
      same while body, because those statements will run first on the next
      iteration
    """
    cur = node
    parent = getattr(cur, "parent", None)

    while parent is not None:
        if _node_type(parent) == "While":
            body = getattr(parent, "body", None) or []
            if cur in body:
                if _text_uses_name(getattr(parent, "test", None), name):
                    return True

                idx = body.index(cur)
                next_iter_prefix = body[:idx]
                for stmt in next_iter_prefix:
                    if _stmt_reads_name_before_overwrite(stmt, name):
                        return True

        cur = parent
        parent = getattr(cur, "parent", None)

    return False


def is_unused_assign(node) -> bool:
    """
    Return True if assigned names are not read before being overwritten
    or before the relevant control-flow scope ends.

    Heuristic only. Handles:
    - simple reassignment flows: x = x.strip()
    - unpacking assignments
    - reads in conditions before branch-local reassignment
    - values assigned in branches and used after branch merge
    - values assigned in nested blocks and used after outer block completion
    - loop-carried state updates in while loops
    """
    if not is_local_function_assignment(node):
        return False

    target_names = [name for name in _assignment_target_names(node) if name and name != "_"]
    if not target_names:
        return False

    parent = getattr(node, "parent", None)
    body = getattr(parent, "body", None)
    if not isinstance(body, list):
        return False

    try:
        idx = body.index(node)
    except ValueError:
        return False

    local_following = body[idx + 1:]

    for name in target_names:
        read_before_overwrite = False
        overwritten_before_read = False

        for stmt in local_following:
            if _stmt_reads_name_before_overwrite(stmt, name):
                read_before_overwrite = True
                break

            if _stmt_assigns_name(stmt, name):
                overwritten_before_read = True
                break

        if not read_before_overwrite and _is_name_used_by_enclosing_while_next_iteration(node, name):
            read_before_overwrite = True

        if not read_before_overwrite and _is_name_read_after_enclosing_control_flow(node, name):
            read_before_overwrite = True

        if not read_before_overwrite and overwritten_before_read:
            return True

        if not read_before_overwrite and not overwritten_before_read:
            return True

    return False


# ===== Scope and symbol helpers =====
def _iter_scope_locals(scope_node) -> Iterable[str]:
    """Yield names defined directly in the given scope."""
    body = getattr(scope_node, "body", None) or []

    for stmt in body:
        stmt_type = _node_type(stmt)

        if stmt_type in {"FunctionDef", "AsyncFunctionDef", "ClassDef"}:
            name = _node_name(stmt)
            if name:
                yield name
            continue

        if stmt_type in {"Assign", "AnnAssign"}:
            for target in _assignment_targets(stmt):
                name = _node_name(target)
                if name:
                    yield name
            continue

        if stmt_type in {"Import", "ImportFrom"}:
            for alias in getattr(stmt, "names", []) or []:
                if isinstance(alias, tuple):
                    original, asname = alias
                    yield asname or original.split(".")[0]


def get_enclosing_scope(node):
    """Return the nearest enclosing lexical scope node."""
    cur = getattr(node, "parent", None)
    while cur is not None:
        if _node_type(cur) in {"FunctionDef", "AsyncFunctionDef", "Module", "Lambda"}:
            return cur
        cur = getattr(cur, "parent", None)
    return None


def is_name_shadowed_in_scope(node, name: str) -> bool:
    """Return True if `name` is defined in the enclosing lexical scope."""
    scope = get_enclosing_scope(node)
    if scope is None:
        return False

    if _node_type(scope) in {"FunctionDef", "AsyncFunctionDef", "Lambda"}:
        args = getattr(scope, "args", None)
        if args is not None:
            for seq_name in ("posonlyargs", "args", "kwonlyargs"):
                for arg in getattr(args, seq_name, []) or []:
                    if _node_name(arg) == name:
                        return True

            for arg in (getattr(args, "vararg", None), getattr(args, "kwarg", None)):
                if _node_name(arg) == name:
                    return True

    return name in set(filter(None, _iter_scope_locals(scope)))


def is_name_rebound_in_scope(node, name: str) -> bool:
    """
    Return True if `name` is rebound in the enclosing lexical scope in a way that
    should suppress builtin/module-name based security heuristics.

    Unlike `is_name_shadowed_in_scope`, this intentionally ignores imports such as
    `import os` or `import random`, because those are the normal, desired uses
    for rules that target module-qualified calls.
    """
    scope = get_enclosing_scope(node)
    if scope is None:
        return False

    if _node_type(scope) in {"FunctionDef", "AsyncFunctionDef", "Lambda"}:
        args = getattr(scope, "args", None)
        if args is not None:
            for seq_name in ("posonlyargs", "args", "kwonlyargs"):
                for arg in getattr(args, seq_name, []) or []:
                    if _node_name(arg) == name:
                        return True

            for arg in (getattr(args, "vararg", None), getattr(args, "kwarg", None)):
                if _node_name(arg) == name:
                    return True

    for stmt in getattr(scope, "body", None) or []:
        stmt_type = _node_type(stmt)

        if stmt_type in {"Assign", "AnnAssign"}:
            for target in _assignment_targets(stmt):
                if _node_name(target) == name:
                    return True
            continue

        if stmt_type in {"FunctionDef", "AsyncFunctionDef", "ClassDef"}:
            if _node_name(stmt) == name:
                return True

    return False


# ===== Empty block helpers =====
def is_noop_stmt(stmt) -> bool:
    """Return True if the statement is effectively a no-op."""
    if _node_type(stmt) == "Pass":
        return True

    if _node_type(stmt) == "Expr":
        value = getattr(stmt, "value", None)
        return isinstance(getattr(value, "value", None), str)

    return False


def is_empty_seq(seq) -> bool:
    """Return True if the sequence is empty or contains only no-op statements."""
    if not seq:
        return True
    return all(is_noop_stmt(stmt) for stmt in seq)


def iter_relevant_bodies(node) -> Iterable[tuple[str, list]]:
    """
    Yield named statement bodies relevant for empty-block analysis.

    Examples include `body`, `orelse`, exception handler bodies, and `finalbody`.
    """
    if hasattr(node, "body"):
        yield ("body", getattr(node, "body") or [])

    node_type = _node_type(node)

    if node_type == "If":
        yield ("orelse", getattr(node, "orelse") or [])

    if node_type == "Try":
        handlers = getattr(node, "handlers", []) or []
        for i, handler in enumerate(handlers):
            yield (f"handler[{i}]", getattr(handler, "body", []) or [])
        yield ("finalbody", getattr(node, "finalbody", []) or [])


def iter_required_bodies(node) -> Iterable[tuple[str, list]]:
    """
    Yield only block bodies whose emptiness should count as an empty block.

    This excludes optional parts such as `try.finalbody`, which may be absent
    without making the overall block empty.
    """
    node_type = _node_type(node)

    if hasattr(node, "body"):
        yield ("body", getattr(node, "body") or [])

    if node_type == "If":
        orelse = getattr(node, "orelse", None) or []
        if orelse:
            yield ("orelse", orelse)

    if node_type == "Try":
        handlers = getattr(node, "handlers", []) or []
        for i, handler in enumerate(handlers):
            yield (f"handler[{i}]", getattr(handler, "body", []) or [])


def is_empty_block(node) -> bool:
    """Return True if any required body of the node is empty or contains only no-op statements."""
    if _node_type(node) not in BLOCK_TYPES:
        return False

    for _, seq in iter_required_bodies(node):
        if is_empty_seq(seq):
            return True

    return False


def empty_parts(node) -> list[str]:
    """Return names of required block parts that are empty or contain only no-op statements."""
    parts: list[str] = []
    for name, seq in iter_required_bodies(node):
        if is_empty_seq(seq):
            parts.append(name)
    return parts


# ===== Control-flow helpers =====
def is_terminal_stmt(stmt) -> bool:
    """Return True if the statement terminates local control flow."""
    return _node_type(stmt) in TERMINAL


def body_ends_terminal(seq) -> bool:
    """Return True if the last statement in the sequence is terminal."""
    seq = seq or []
    return bool(seq) and is_terminal_stmt(seq[-1])


def has_redundant_else_after_terminal(node) -> bool:
    """
    Return True if an if/elif/else chain contains an unnecessary else branch
    after a terminal statement.
    """
    if _node_type(node) != "If":
        return False

    orelse = getattr(node, "orelse", []) or []
    if not orelse:
        return False

    if _node_type(orelse[0]) != "If":
        return body_ends_terminal(getattr(node, "body", []) or [])

    cur = node
    while True:
        if not body_ends_terminal(getattr(cur, "body", []) or []):
            return False

        tail = getattr(cur, "orelse", []) or []
        if not tail:
            return False

        if _node_type(tail[0]) != "If":
            return True

        cur = tail[0]


def count_returns_in_function(node, *, stop_after: int | None = None) -> int:
    """
    Count return statements inside a function while ignoring nested scopes.

    Nested functions and classes are not traversed.
    """
    if _node_type(node) not in {"FunctionDef", "AsyncFunctionDef"}:
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

        cur_type = _node_type(cur)
        if cur_type == "Return":
            count += 1
            if stop_after is not None and count >= stop_after:
                return count

        if cur_type in STOP_TYPES and cur is not node:
            continue

        for child in cur.get_children():
            stack.append(child)

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

    numbers: list[int] = []
    for i, line in enumerate(content.splitlines(), start=1):
        if len(line.rstrip("\n")) > max_len:
            numbers.append(i)

    return numbers


def has_long_lines(node, max_len: int) -> bool:
    """Return True if the source file contains any line longer than the given limit."""
    return bool(long_line_numbers(node, max_len))


# ===== Constant and whitespace helpers =====
def is_module_constant(node) -> bool:
    """
    Return True if the node represents a simple module-level constant assignment.

    Dunder names are excluded.
    """
    if _node_type(getattr(node, "parent", None)) != "Module":
        return False

    if _node_type(node) not in {"Assign", "AnnAssign"}:
        return False

    targets = _assignment_targets(node)
    if len(targets) != 1:
        return False

    name = _node_name(targets[0])
    if not name or (name.startswith("__") and name.endswith("__")):
        return False

    value = getattr(node, "value", None)
    return _node_type(value) in {
        "Const",
        "Constant",
        "Num",
        "Str",
        "Bytes",
        "Tuple",
        "List",
        "Set",
        "Dict",
    }


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
    """Rewrite suggestion lines with trailing spaces and tabs removed from line ends."""
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

    required = 1 if _node_type(parent) == "ClassDef" else 2
    prev_end = getattr(prev, "end_lineno", getattr(prev, "lineno", 0))
    cur_line = getattr(node, "lineno", 0)

    if cur_line <= prev_end + 1:
        blanks = 0
    else:
        lines = content.splitlines()
        lo = max(1, prev_end + 1)
        hi = min(len(lines), cur_line - 1)
        blanks = sum(1 for i in range(lo, hi + 1) if lines[i - 1].strip() == "")

    return blanks < required


def missing_blank_before_def_comment(node) -> str:
    """Return an explanatory comment for a missing blank line before a definition."""
    parent = getattr(node, "parent", None)
    required = 1 if _node_type(parent) == "ClassDef" else 2
    return f"# Missing blank line(s) before this definition (PEP 8: require {required} here)."


def insert_function_docstring(node, suggestion_lines, context, **kwargs):
    """Insert a generated docstring into a function definition suggestion."""
    text = kwargs.get("text") or '"""TODO: Describe the function."""'
    if not suggestion_lines:
        return

    indent = " " * (getattr(node, "col_offset", 0) + 4)
    signature = suggestion_lines[0]

    if ":" in signature and not signature.strip().endswith(":"):
        before, after = signature.split(":", 1)
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
    signature = suggestion_lines[0]

    if ":" in signature and not signature.strip().endswith(":"):
        before, after = signature.split(":", 1)
        suggestion_lines[0] = f"{before}:"
        suggestion_lines.insert(1, f"{indent}{text}")
        rest = after.strip()
        if rest:
            suggestion_lines.insert(2, f"{indent}{rest}")
        return

    suggestion_lines.insert(1, f"{indent}{text}")


# ===== Compare helpers =====
def _is_none_const(node) -> bool:
    """Return True if the node represents the literal value None."""
    return (
        node is not None
        and _node_type(node) in {"Const", "Constant", "NameConstant"}
        and getattr(node, "value", "___") is None
    )


def _iter_compare_pairs(node) -> Iterable[tuple[str, object, object]]:
    """
    Yield normalized comparison pairs from a Compare node.

    Each yielded item is `(operator_name, left, right)`.
    Supports both astroid-style and tuple-based comparison representations.
    """
    if _node_type(node) != "Compare":
        return

    left = getattr(node, "left", None)
    ops = getattr(node, "ops", []) or []
    comparators = getattr(node, "comparators", None)

    if comparators is not None:
        prev = left
        for i, op in enumerate(ops):
            if i >= len(comparators):
                break
            op_name = _node_type(op)
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
            op_name = _node_type(op_raw)

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

    if ignore_init and _node_name(node) == "__init__":
        return 0

    posonly_args = list(getattr(args, "posonlyargs", []) or [])
    normal_args = list(getattr(args, "args", []) or [])
    kwonly_args = list(getattr(args, "kwonlyargs", []) or [])

    count = len(posonly_args) + len(normal_args) + len(kwonly_args)

    if ignore_bound_first_arg and normal_args:
        first_name = _node_name(normal_args[0])
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
        if _node_type(node) not in {"FunctionDef", "AsyncFunctionDef"}:
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
            if _node_type(parent) in allowed:
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

        stmt_type = _node_type(stmt)
        if stmt_type in {"FunctionDef", "AsyncFunctionDef", "ClassDef"}:
            return 0

        total = 1

        for attr in ("body", "orelse", "finalbody"):
            seq = getattr(stmt, attr, None)
            if isinstance(seq, list):
                total += sum(_count_stmt(child) for child in seq)

        handlers = getattr(stmt, "handlers", None) or []
        for handler in handlers:
            total += sum(_count_stmt(child) for child in (getattr(handler, "body", None) or []))

        return total

    body = getattr(node, "body", None) or []
    return sum(_count_stmt(stmt) for stmt in body)


# ===== Performance-specific helpers =====
def _previous_sibling_statement(node):
    """Return the previous sibling statement in the same body, if present."""
    parent = getattr(node, "parent", None)
    if parent is None or not hasattr(parent, "body"):
        return None

    parent_body = list(getattr(parent, "body", []) or [])
    try:
        index = parent_body.index(node)
    except ValueError:
        return None

    return parent_body[index - 1] if index > 0 else None


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

    value_type = _node_type(init_value)

    if value_type == "List":
        return "list"

    if value_type == "Dict":
        return "dict"

    if value_type == "Call":
        func_name = _node_name(getattr(init_value, "func", None))
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
        ("list", expr_text)
        ("set", expr_text)
        ("dict", key_text, value_text)
        or None
    """
    stmt_type = _node_type(stmt)

    if stmt_type == "Expr":
        call = getattr(stmt, "value", None)
        if _node_type(call) != "Call":
            return None

        func = getattr(call, "func", None)
        if _node_type(func) != "Attribute":
            return None

        base = getattr(func, "expr", None) or getattr(func, "value", None)
        if _node_name(base) != acc_name:
            return None

        args = getattr(call, "args", []) or []
        if len(args) != 1:
            return None

        expr_text = _node_text(args[0])
        if not expr_text:
            return None

        method_name = _attr_name(func)
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
        if _node_type(target) != "Subscript":
            return None

        base = getattr(target, "value", None) or getattr(target, "expr", None)
        if _node_name(base) != acc_name:
            return None

        key_node = getattr(target, "slice", None) or getattr(target, "index", None)
        key_text = _node_text(key_node)
        value_text = _node_text(getattr(stmt, "value", None))

        if key_text and value_text:
            return ("dict", key_text, value_text)

    return None


def _extract_loop_filter_and_stmt(for_node):
    """
    Extract an optional filter condition and the single effective body statement.

    Returns:
        tuple[str | None, object | None]:
            (condition_text, effective_stmt)

    The loop must contain exactly one statement.
    If that statement is `if`, it must:
    - have no else branch
    - contain exactly one statement in its body
    """
    loop_body = getattr(for_node, "body", None) or []
    if len(loop_body) != 1:
        return (None, None)

    stmt = loop_body[0]
    if _node_type(stmt) != "If":
        return (None, stmt)

    if getattr(stmt, "orelse", None):
        return (None, None)

    if_body = getattr(stmt, "body", None) or []
    if len(if_body) != 1:
        return (None, None)

    condition_text = _node_text(getattr(stmt, "test", None))
    if not condition_text:
        return (None, None)

    return (condition_text, if_body[0])


def _build_comprehension_suggestion(
    *,
    kind: str,
    acc_name: str,
    target_text: str,
    iter_text: str,
    condition_text: str | None,
    extracted,
) -> tuple[str | None, str | None]:
    """Build the final comprehension suggestion string."""
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


def loop_comprehension_suggestion(for_node):
    """
    Suggest a list, set, or dict comprehension replacement for a simple loop.

    Returns:
        tuple[str | None, str | None]:
            Pair of (kind, suggestion), or (None, None) if no safe rewrite pattern is found.
    """
    if _node_type(for_node) != "For":
        return (None, None)

    prev_stmt = _previous_sibling_statement(for_node)
    if _node_type(prev_stmt) != "Assign":
        return (None, None)

    prev_targets = getattr(prev_stmt, "targets", None) or []
    if len(prev_targets) != 1:
        return (None, None)

    acc_name = _node_name(prev_targets[0])
    if not acc_name:
        return (None, None)

    kind = _infer_comprehension_accumulator_kind(getattr(prev_stmt, "value", None))
    if not kind:
        return (None, None)

    condition_text, effective_stmt = _extract_loop_filter_and_stmt(for_node)
    if effective_stmt is None:
        return (None, None)

    extracted = _extract_single_collection_build_stmt(effective_stmt, acc_name)
    if not extracted:
        return (None, None)

    target_text = _node_text(getattr(for_node, "target", None)) or "_"
    iter_text = _node_text(getattr(for_node, "iter", None)) or "iterable"

    return _build_comprehension_suggestion(
        kind=kind,
        acc_name=acc_name,
        target_text=target_text,
        iter_text=iter_text,
        condition_text=condition_text,
        extracted=extracted,
    )


def is_loop_comprehension_candidate(for_node) -> bool:
    """Return True if the loop can be rewritten as a comprehension."""
    kind, suggestion = loop_comprehension_suggestion(for_node)
    return bool(kind and suggestion)


def _assigned_names_in_statements(statements) -> set[str]:
    """Collect simple assigned names from a sequence of statements."""
    names: set[str] = set()

    for stmt in statements or []:
        if _node_type(stmt) not in {"Assign", "AnnAssign"}:
            continue

        for target in _assignment_targets(stmt):
            name = _node_name(target)
            if name:
                names.add(name)

    return names


def is_nested_loop_same_stable_collection(node) -> bool:
    """
    Return True when an inner loop iterates over the same stable collection
    as an enclosing outer loop.
    """
    if _node_type(node) != "For":
        return False

    outer = getattr(node, "parent", None)
    while outer is not None and _node_type(outer) != "For":
        outer = getattr(outer, "parent", None)

    if outer is None:
        return False

    inner_iter = getattr(node, "iter", None)
    outer_iter = getattr(outer, "iter", None)
    if inner_iter is None or outer_iter is None:
        return False

    if _node_type(inner_iter) == "Call" or _node_type(outer_iter) == "Call":
        return False

    if _node_text(inner_iter) != _node_text(outer_iter):
        return False

    if _node_type(inner_iter) == "Name":
        iter_name = _node_name(inner_iter)
        outer_body = getattr(outer, "body", []) or []

        for stmt in outer_body:
            if stmt is node:
                break
            if iter_name in _assigned_names_in_statements([stmt]):
                return False

    return True


def is_builtin_name_call(node, allowed_names: set[str] | frozenset[str]) -> bool:
    """Return True if node is a call to a non-shadowed builtin name."""
    if _node_type(node) != "Call":
        return False

    func = getattr(node, "func", None)
    if _node_type(func) != "Name":
        return False

    called = _node_name(func)
    return called in allowed_names and not is_name_shadowed_in_scope(node, called)


def is_builtin_print_call(node) -> bool:
    """Return True if node is a call to builtin print()."""
    return is_builtin_name_call(node, {"print"})


def is_redundant_sorted_before_minmax(node) -> bool:
    """Return True for min(sorted(x)) / max(sorted(x)) with non-shadowed builtins."""
    if not is_builtin_name_call(node, {"min", "max"}):
        return False

    args = getattr(node, "args", []) or []
    if len(args) != 1:
        return False

    inner = args[0]
    return _node_type(inner) == "Call" and is_builtin_name_call(inner, {"sorted"})


def is_probably_str_join_call(node) -> bool:
    """Return True for calls of the form '<string-literal>.join(...)'."""
    if _node_type(node) != "Call":
        return False

    func = getattr(node, "func", None)
    if _node_type(func) != "Attribute":
        return False

    base = getattr(func, "expr", None) or getattr(func, "value", None)
    return _attr_name(func) == "join" and isinstance(getattr(base, "value", None), str)


# ===== Security-specific helpers =====
def is_builtin_eval_or_exec_call(node) -> bool:
    """Return True if node is a call to non-shadowed builtin eval() or exec()."""
    return is_builtin_name_call(node, {"eval", "exec"})


def is_explicit_builtins_eval_or_exec_call(node) -> bool:
    """Return True for calls like builtins.eval(...) or builtins.exec(...)."""
    if _node_type(node) != "Call":
        return False

    func = getattr(node, "func", None)
    if _node_type(func) != "Attribute":
        return False

    base = getattr(func, "expr", None) or getattr(func, "value", None)
    return _node_name(base) == "builtins" and _attr_name(func) in {"eval", "exec"}


def is_builtin_eval_literal_candidate(node) -> bool:
    """Return True for non-shadowed eval('<literal-like>') candidates."""
    if not is_builtin_name_call(node, {"eval"}):
        return False

    args = getattr(node, "args", None) or []
    keywords = getattr(node, "keywords", None) or []
    if len(args) != 1 or keywords:
        return False

    arg = args[0]
    if _node_type(arg) not in {"Const", "Constant"}:
        return False

    value = getattr(arg, "value", None)
    if not isinstance(value, str):
        return False

    text = value.strip()
    if not text:
        return False

    return text[0] in "([{'\"-0123456789"


def is_builtin_os_system_or_popen_call(node) -> bool:
    """Return True for calls like os.system(...) or os.popen(...), excluding local rebinding of `os`."""
    if _node_type(node) != "Call":
        return False

    func = getattr(node, "func", None)
    if _node_type(func) != "Attribute":
        return False

    base = getattr(func, "expr", None) or getattr(func, "value", None)
    return (
        _node_name(base) == "os"
        and not is_name_rebound_in_scope(node, "os")
        and _attr_name(func) in {"system", "popen"}
    )


def is_probable_secret_target_name(name: str, suspect_names: tuple[str, ...]) -> bool:
    """Return True if identifier contains a secret-like semantic part."""
    lowered = name.lower()
    parts = split_identifier_parts(name)
    suspects = {s.lower() for s in suspect_names}

    if lowered in suspects:
        return True

    return any(part in suspects for part in parts)


def is_hardcoded_secret_assignment(node, suspect_names: tuple[str, ...]) -> bool:
    """Return True for assignments of non-empty string literals to secret-like names."""
    if _node_type(node) not in {"Assign", "AnnAssign"}:
        return False

    targets = _assignment_targets(node)
    if len(targets) != 1:
        return False

    name = _node_name(targets[0])
    if not name or not is_probable_secret_target_name(name, suspect_names):
        return False

    value = getattr(node, "value", None)
    if _node_type(value) not in {"Const", "Constant"}:
        return False

    literal = getattr(value, "value", None)
    return isinstance(literal, str) and bool(literal.strip())


def is_insecure_random_call(node, unsafe_funcs: set[str]) -> bool:
    """Return True for calls like random.choice(...), excluding local rebinding of `random`."""
    if _node_type(node) != "Call":
        return False

    func = getattr(node, "func", None)
    if _node_type(func) != "Attribute":
        return False

    base = getattr(func, "expr", None) or getattr(func, "value", None)
    return (
        _node_name(base) == "random"
        and not is_name_rebound_in_scope(node, "random")
        and _attr_name(func) in unsafe_funcs
    )


def is_builtin_open_call(node) -> bool:
    """Return True if node is a call to non-shadowed builtin open()."""
    return is_builtin_name_call(node, {"open"})
