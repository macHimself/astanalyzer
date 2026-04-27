"""
Internal action application logic for FixerBuilder.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from ..tools import _is_none_const, _iter_compare_pairs
from .types import FixAction, FixContext

log = logging.getLogger(__name__)


class FixerActionsMixin:
    """Internal mixin with concrete action handlers for fixer operations."""

    def _apply_action(self, node: Any, action: FixAction, context: FixContext) -> None:
        dispatch = {
            "insert_before": self._apply_insert_before,
            "insert_after": self._apply_insert_after,
            "append": self._apply_append,
            "prepend": self._apply_prepend,
            "replace_with": self._apply_replace_with,
            "replace_line": self._apply_replace_line,
            "comment_before": self._apply_comment_before,
            "comment_after": self._apply_comment_after,
            "add_docstring": self._apply_add_docstring,
            "remove_line": self._apply_remove_line,
            "delete_node": self._apply_delete_node,
            "remove_dead_code_after": self._apply_remove_dead_code_after,
            "insert_at_body_start": self._apply_insert_at_body_start,
            "remove_orelse_header": self._apply_remove_orelse_header,
            "unindent_orelse": self._apply_unindent_orelse,
            "remove_block_header": self._apply_remove_block_header,
            "unindent_block": self._apply_unindent_block,
            "comment_on_function": self._apply_comment_on_function,
            "strip_trailing_whitespace": self._apply_strip_trailing_whitespace,
            "insert_blank_line_before": self._apply_insert_blank_line_before,
            "add_module_docstring": self._apply_add_module_docstring,
            "replace_with_value": self._apply_replace_with_value,
            "flatten_always_true_if": self._apply_flatten_always_true_if,
            "replace_none_comparison_operator": self._apply_replace_none_comparison_operator,
            "replace_node_text": self._apply_replace_node_text,
            "replace_range": self._apply_replace_range,
            "remove_node": self._apply_remove_node,
            "remove_except_alias": self._apply_remove_except_alias,
            "replace_bare_except_with_exception": self._apply_replace_bare_except_with_exception,
            "replace_mutable_default_with_none": self._apply_replace_mutable_default_with_none,
            "insert_mutable_default_guard": self._apply_insert_mutable_default_guard,
            "replace_print_listcomp_with_for_loop": self._apply_replace_print_listcomp_with_for_loop,
            "remove_redundant_sorted": self._apply_remove_redundant_sorted,
            "replace_unnecessary_copy": self._apply_replace_unnecessary_copy,
            "replace_join_listcomp_with_generator": self._apply_replace_join_listcomp_with_generator,
            "replace_eval_with_literal_eval": self._apply_replace_eval_with_literal_eval,
            "ensure_import": self._apply_ensure_import,
            "replace_os_system_with_subprocess_template": self._apply_replace_os_system_with_subprocess_template,
            "replace_os_system_with_subprocess_run": self._apply_replace_os_system_with_subprocess_run,
            "review_note_and_ignore": self._apply_review_note_and_ignore,
        }
        handler = dispatch.get(action.kind)
        if handler:
            handler(node, action, context)

    def _get_working_text(self, node: Any, context: FixContext) -> str:
        if context.working_text is not None:
            return context.working_text

        source_text = getattr(node.root(), "file_content", "")
        if source_text:
            return source_text

        return context.original or ""

    def _get_context_text(self, node: Any, context: FixContext) -> str:
        if context.full_file_mode:
            return "\n".join(context.suggestion_lines)

        source_text = getattr(node.root(), "file_content", "")
        if source_text:
            return source_text

        return "\n".join(context.suggestion_lines)

    def _has_import(self, lines: list[str], module: str) -> bool:
        pattern_import = re.compile(rf"^\s*import\s+{re.escape(module)}\b")
        pattern_from = re.compile(rf"^\s*from\s+{re.escape(module)}\s+import\b")

        for line in lines:
            if pattern_import.match(line):
                return True
            if pattern_from.match(line):
                return True

        return False

    def _find_import_insertion_index(self, lines: list[str]) -> int:
        if not lines:
            return 0

        i = 0

        if i < len(lines) and lines[i].startswith("#!"):
            i += 1

        if i < len(lines) and "coding" in lines[i]:
            i += 1

        while i < len(lines) and lines[i].strip() == "":
            i += 1

        if i < len(lines):
            stripped = lines[i].lstrip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                quote = '"""' if stripped.startswith('"""') else "'''"

                if stripped.count(quote) >= 2 and len(stripped) > len(quote):
                    i += 1
                else:
                    i += 1
                    while i < len(lines):
                        if quote in lines[i]:
                            i += 1
                            break
                        i += 1

        while i < len(lines) and lines[i].strip() == "":
            i += 1

        j = i
        while j < len(lines):
            stripped = lines[j].strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                j += 1
                continue
            if stripped == "":
                next_j = j + 1
                if next_j < len(lines):
                    next_stripped = lines[next_j].strip()
                    if next_stripped.startswith("import ") or next_stripped.startswith("from "):
                        j += 1
                        continue
                break
            break

        return j

    def _replace_node_range_in_context(self, node: Any, replacement: str, context: FixContext) -> None:
        source_text = self._get_working_text(node, context)
        if not source_text:
            return

        lineno = getattr(node, "lineno", None)
        col = getattr(node, "col_offset", None)
        end_lineno = getattr(node, "end_lineno", None)
        end_col = getattr(node, "end_col_offset", None)

        if None in (lineno, col, end_lineno, end_col):
            return

        lines = source_text.splitlines(keepends=True)

        if lineno - 1 < 0 or end_lineno - 1 >= len(lines):
            return

        start_offset = sum(len(lines[i]) for i in range(lineno - 1)) + col
        end_offset = sum(len(lines[i]) for i in range(end_lineno - 1)) + end_col

        new_text = source_text[:start_offset] + replacement + source_text[end_offset:]

        context.working_text = new_text
        context.suggestion_lines[:] = new_text.splitlines()
        context.full_file_mode = True

    def _get_original_source(self, node: Any) -> str:
        source_text = getattr(node.root(), "file_content", "")
        if source_text:
            lines = source_text.splitlines()
            start = max(0, getattr(node, "lineno", 1) - 1)
            end = getattr(node, "end_lineno", start + 1)
            return "\n".join(lines[start:end])

        try:
            return node.as_string().rstrip()
        except Exception:
            return ""

    def _get_call_name(self, node: Any) -> str | None:
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

    def _get_block_nodes(self, node: Any, attr: str) -> list[Any]:
        value = getattr(node, attr, None)

        if value is None:
            return []

        if isinstance(value, list):
            return value

        return [value]

    def _is_docstring_stmt(self, node) -> bool:
        if node.__class__.__name__ != "Expr":
            return False

        value = getattr(node, "value", None)
        if value is None:
            return False

        cname = value.__class__.__name__
        if cname not in ("Const", "Constant", "Str"):
            return False

        return isinstance(getattr(value, "value", None), str)

    def _find_block_header_index(self, node: Any, context: FixContext, attr: str) -> int | None:
        block_nodes = self._get_block_nodes(node, attr)
        if not block_nodes:
            return None

        node_lineno = getattr(node, "lineno", 1)
        first_lineno = getattr(block_nodes[0], "lineno", None)
        if first_lineno is None:
            return None

        candidate = first_lineno - node_lineno - 1
        if candidate < 0 or candidate >= len(context.suggestion_lines):
            return None

        line = context.suggestion_lines[candidate].lstrip()
        expected_headers = {
            "orelse": ("else:", "elif"),
            "finalbody": ("finally:",),
        }

        allowed = expected_headers.get(attr, ())
        if allowed and any(line.startswith(prefix) for prefix in allowed):
            return candidate

        return None

    def _find_orelse_header_index(self, node: Any, context: FixContext) -> int | None:
        orelse = getattr(node, "orelse", None) or []
        if not orelse:
            return None

        node_lineno = getattr(node, "lineno", 1)
        first_orelse_lineno = getattr(orelse[0], "lineno", None)
        if first_orelse_lineno is None:
            return None

        candidate = first_orelse_lineno - node_lineno - 1
        if 0 <= candidate < len(context.suggestion_lines):
            line = context.suggestion_lines[candidate]
            if line.lstrip().startswith("else:"):
                return candidate

        for i, line in enumerate(context.suggestion_lines):
            if line.lstrip().startswith("else:"):
                return i

        return None

    @staticmethod
    def _validate_single_line(text: str, method_name: str) -> None:
        if not isinstance(text, str):
            raise TypeError(f"{method_name}(text): text must be a string")
        if "\n" in text or "\r" in text:
            raise ValueError(
                f"{method_name}(text) expects a single line without newline characters"
            )

    @staticmethod
    def _make_lines(text: str, indent: int = 0, comment: str | None = None) -> list[str]:
        indent_str = " " * indent
        lines: list[str] = []
        if comment:
            lines.append(f"{indent_str}# {comment}")
        lines.append(f"{indent_str}{text}")
        return lines

    def _apply_insert_before(self, node: Any, action: FixAction, context: FixContext) -> None:
        lines = self._make_lines(
            action.params["text"],
            action.params.get("indent", 0),
            action.params.get("comment"),
        )
        context.suggestion_lines[0:0] = lines

    def _apply_insert_after(self, node: Any, action: FixAction, context: FixContext) -> None:
        lines = self._make_lines(
            action.params["text"],
            action.params.get("indent", 0),
            action.params.get("comment"),
        )
        context.suggestion_lines.extend(lines)

    def _apply_append(self, node: Any, action: FixAction, context: FixContext) -> None:
        self._apply_insert_after(node, action, context)

    def _apply_prepend(self, node: Any, action: FixAction, context: FixContext) -> None:
        self._apply_insert_before(node, action, context)

    def _apply_replace_with(self, node: Any, action: FixAction, context: FixContext) -> None:
        text = action.params["text"]
        context.suggestion_lines[:] = text.splitlines()

    def _apply_replace_line(self, node: Any, action: FixAction, context: FixContext) -> None:
        line_parts = self._make_lines(
            action.params["text"],
            action.params.get("indent", 0),
            action.params.get("comment"),
        )
        if context.suggestion_lines:
            context.suggestion_lines[:1] = line_parts
        else:
            context.suggestion_lines[:] = line_parts

    def _apply_comment_before(self, node: Any, action: FixAction, context: FixContext) -> None:
        indent = " " * getattr(node, "col_offset", 0)
        context.suggestion_lines.insert(0, f"{indent}# {action.params['text']}")

    def _apply_comment_after(self, node: Any, action: FixAction, context: FixContext) -> None:
        indent = " " * getattr(node, "col_offset", 0)
        context.suggestion_lines.append(f"{indent}# {action.params['text']}")

    def _apply_review_note_and_ignore(self, node: Any, action: FixAction, context: FixContext) -> None:
        indent = " " * getattr(node, "col_offset", 0)

        rule_id = action.params["rule_id"]
        text_builder = action.params["text"]

        text = text_builder(node) if callable(text_builder) else text_builder
        if not text:
            return

        if not text.lstrip().startswith("#"):
            text = f"# {text}"

        context.suggestion_lines.insert(0, f"{indent}# astanalyzer: ignore-next {rule_id}")
        context.suggestion_lines.insert(0, f"{indent}{text}")

    def _apply_add_docstring(self, node: Any, action: FixAction, context: FixContext) -> None:
        doc = action.params["text"]

        body = getattr(node, "body", None)
        if not body:
            return

        first_stmt = body[0]

        node_lineno = getattr(node, "lineno", 1)
        first_lineno = getattr(first_stmt, "lineno", node_lineno)

        insert_at = max(1, first_lineno - node_lineno)
        indent = getattr(first_stmt, "col_offset", getattr(node, "col_offset", 0) + 4)
        doc_line = " " * indent + doc

        context.suggestion_lines.insert(insert_at, doc_line)

    def _apply_remove_line(self, node: Any, action: FixAction, context: FixContext) -> None:
        if context.suggestion_lines:
            del context.suggestion_lines[0]

    def _apply_delete_node(self, node: Any, action: FixAction, context: FixContext) -> None:
        context.delete_entirely = True

    def _apply_insert_at_body_start(self, node: Any, action: FixAction, context: FixContext) -> None:
        body = getattr(node, "body", None) or []
        if not body:
            return

        first_stmt = body[0]

        node_lineno = getattr(node, "lineno", 1)
        first_lineno = getattr(first_stmt, "lineno", node_lineno)
        insert_at = max(1, first_lineno - node_lineno)

        indent = getattr(first_stmt, "col_offset", getattr(node, "col_offset", 0) + 4)

        lines = self._make_lines(
            action.params["text"],
            indent,
            action.params.get("comment"),
        )
        context.suggestion_lines[insert_at:insert_at] = lines

    def _apply_comment_on_function(self, node: Any, action: FixAction, context: FixContext) -> None:
        text = action.params["text"]
        if not text:
            return

        comment_line = text if text.lstrip().startswith("#") else f"# {text}"

        decorators = getattr(node, "decorators", None)
        decorator_nodes = getattr(decorators, "nodes", None) if decorators is not None else None
        insert_at = len(decorator_nodes) if decorator_nodes else 0

        context.suggestion_lines.insert(insert_at, comment_line)

    def _apply_strip_trailing_whitespace(self, node: Any, action: FixAction, context: FixContext) -> None:
        context.suggestion_lines[:] = [line.rstrip(" \t") for line in context.suggestion_lines]

    def _apply_insert_blank_line_before(self, node: Any, action: FixAction, context: FixContext) -> None:
        context.suggestion_lines.insert(0, "")

    def _apply_replace_with_value(self, node: Any, action: FixAction, context: FixContext) -> None:
        value = getattr(node, "value", None)
        if value is None:
            return

        try:
            replacement = value.as_string().rstrip()
        except Exception:
            return

        context.suggestion_lines[:] = replacement.splitlines()

    def _apply_add_module_docstring(self, node: Any, action: FixAction, context: FixContext) -> None:
        doc = action.params["text"]
        lines = context.suggestion_lines

        if not lines:
            context.suggestion_lines[:] = [doc]
            return

        insert_at = 0
        if lines and lines[0].startswith("#!"):
            insert_at = 1

        if insert_at < len(lines) and "coding" in lines[insert_at]:
            insert_at += 1

        if insert_at == 0:
            context.suggestion_lines[insert_at:insert_at] = [doc, ""]
        else:
            context.suggestion_lines[insert_at:insert_at] = [doc]

    def _apply_flatten_always_true_if(self, node: Any, action: FixAction, context: FixContext) -> None:
        if node.__class__.__name__ != "If":
            return

        body = getattr(node, "body", None) or []
        if not body:
            return

        source_text = getattr(node.root(), "file_content", "")
        if not source_text:
            return

        file_lines = source_text.splitlines()

        body_start = getattr(body[0], "lineno", None)
        body_end = getattr(body[-1], "end_lineno", getattr(body[-1], "lineno", None))
        node_start = getattr(node, "lineno", None)
        node_end = getattr(node, "end_lineno", None)

        if None in (body_start, body_end, node_start, node_end):
            return

        body_lines = file_lines[body_start - 1:body_end]

        adjusted: list[str] = []
        for line in body_lines:
            if line.strip():
                adjusted.append(line[4:] if line.startswith("    ") else line.lstrip())
            else:
                adjusted.append("")

        context.original = "\n".join(file_lines[node_start - 1:node_end])
        context.suggestion_lines[:] = adjusted

    def _apply_remove_dead_code_after(self, node: Any, action: FixAction, context: FixContext) -> None:
        parent = getattr(node, "parent", None)
        if not parent or not hasattr(parent, "body"):
            return

        body = getattr(parent, "body", None)
        if not isinstance(body, list):
            return

        try:
            idx = body.index(node)
        except ValueError:
            return

        source_text = getattr(node.root(), "file_content", "")
        if not source_text:
            return

        file_lines = source_text.splitlines()

        first_stmt = body[0]
        last_stmt = body[-1]

        start_line = getattr(first_stmt, "lineno", None)
        end_line = getattr(last_stmt, "end_lineno", getattr(last_stmt, "lineno", None))
        keep_end_line = getattr(node, "end_lineno", getattr(node, "lineno", None))

        if start_line is None or end_line is None or keep_end_line is None:
            return

        original_block_lines = file_lines[start_line - 1:end_line]
        kept_block_lines = file_lines[start_line - 1:keep_end_line]

        context.original = "\n".join(original_block_lines)
        context.suggestion_lines[:] = kept_block_lines

    def _apply_remove_orelse_header(self, node: Any, action: FixAction, context: FixContext) -> None:
        idx = self._find_orelse_header_index(node, context)
        if idx is None:
            return
        del context.suggestion_lines[idx]

    def _apply_remove_block_header(self, node: Any, action: FixAction, context: FixContext) -> None:
        attr = action.params["attr"]
        idx = self._find_block_header_index(node, context, attr)
        if idx is None:
            return
        if 0 <= idx < len(context.suggestion_lines):
            del context.suggestion_lines[idx]

    def _apply_unindent_orelse(self, node: Any, action: FixAction, context: FixContext) -> None:
        orelse = getattr(node, "orelse", None) or []
        if not orelse:
            return

        spaces = action.params.get("spaces", 4)

        node_lineno = getattr(node, "lineno", 1)
        first_orelse_lineno = getattr(orelse[0], "lineno", None)
        last_orelse_end_lineno = getattr(
            orelse[-1],
            "end_lineno",
            getattr(orelse[-1], "lineno", None),
        )

        if first_orelse_lineno is None or last_orelse_end_lineno is None:
            return

        start_idx = first_orelse_lineno - node_lineno
        end_idx = last_orelse_end_lineno - node_lineno

        if start_idx < 0:
            return

        for i in range(start_idx, min(end_idx + 1, len(context.suggestion_lines))):
            line = context.suggestion_lines[i]
            if not line.strip():
                continue

            indent_count = len(line) - len(line.lstrip(" "))
            remove_n = min(spaces, indent_count)
            context.suggestion_lines[i] = line[remove_n:]

    def _apply_unindent_block(self, node: Any, action: FixAction, context: FixContext) -> None:
        attr = action.params["attr"]
        spaces = action.params.get("spaces", 4)

        block_nodes = self._get_block_nodes(node, attr)
        if not block_nodes:
            return

        node_lineno = getattr(node, "lineno", 1)
        first_lineno = getattr(block_nodes[0], "lineno", None)
        last_end_lineno = getattr(
            block_nodes[-1],
            "end_lineno",
            getattr(block_nodes[-1], "lineno", None),
        )

        if first_lineno is None or last_end_lineno is None:
            return

        start_idx = first_lineno - node_lineno
        end_idx = last_end_lineno - node_lineno

        header_idx = self._find_block_header_index(node, context, attr)
        if header_idx is None:
            start_idx -= 1
            end_idx -= 1

        if start_idx < 0:
            return

        for i in range(start_idx, min(end_idx + 1, len(context.suggestion_lines))):
            line = context.suggestion_lines[i]
            if not line.strip():
                continue

            indent_count = len(line) - len(line.lstrip(" "))
            remove_n = min(spaces, indent_count)
            context.suggestion_lines[i] = line[remove_n:]

    def _apply_replace_range(self, node: Any, action: FixAction, context: FixContext) -> None:
        replacement = action.params["text"]
        self._replace_node_range_in_context(node, replacement, context)

    def _apply_replace_node_text(self, node: Any, action: FixAction, context: FixContext) -> None:
        replacement = action.params["text"]
        self._replace_node_range_in_context(node, replacement, context)

    def _apply_replace_none_comparison_operator(self, node: Any, action: FixAction, context: FixContext) -> None:
        if node.__class__.__name__ != "Compare":
            return

        pairs = list(_iter_compare_pairs(node))
        if len(pairs) != 1:
            return

        op_name, left, right = pairs[0]

        left_is_none = _is_none_const(left)
        right_is_none = _is_none_const(right)

        if left_is_none == right_is_none:
            return

        target = right if left_is_none else left

        try:
            target_text = target.as_string().rstrip()
        except Exception:
            return

        if op_name == "Eq":
            replacement = f"{target_text} is None"
        elif op_name == "NotEq":
            replacement = f"{target_text} is not None"
        else:
            return

        self._replace_node_range_in_context(node, replacement, context)

    def _apply_remove_node(self, node, action, context):
        ref_name = action.params["ref"]
        target = context.refs.get(ref_name)

        log.debug("REMOVE_NODE refs=%s", list(context.refs.keys()))
        if target is None:
            log.debug("REMOVE_NODE missing ref=%s", ref_name)
            return

        source_text = getattr(node.root(), "file_content", "")
        if not source_text:
            return

        lines = source_text.splitlines()

        start = getattr(target, "lineno", None)
        end = getattr(target, "end_lineno", start)

        if start is None:
            return

        start_idx = start - 1
        end_idx = end

        new_lines = lines[:start_idx] + lines[end_idx:]

        context.original = source_text
        context.suggestion_lines[:] = new_lines
        context.full_file_mode = True

    def _apply_remove_except_alias(self, node: Any, action: FixAction, context: FixContext) -> None:
        if node.__class__.__name__ != "ExceptHandler":
            return

        source_text = getattr(node.root(), "file_content", "")
        if not source_text:
            return

        lineno = getattr(node, "lineno", None)
        col = getattr(node, "col_offset", None)
        if lineno is None or col is None:
            return

        lines = source_text.splitlines(keepends=True)
        line_idx = lineno - 1
        if line_idx < 0 or line_idx >= len(lines):
            return

        line = lines[line_idx]
        name = getattr(node, "name", None)
        if not name:
            return

        if not isinstance(name, str):
            name = getattr(name, "name", None) or getattr(name, "id", None)

        if not name:
            return

        pattern = rf"(\bexcept\b.*?)(\s+as\s+{re.escape(name)})(\s*:)"
        new_line = re.sub(pattern, r"\1\3", line, count=1)

        if new_line == line:
            return

        new_text = (
            source_text[:sum(len(lines[i]) for i in range(line_idx))]
            + new_line
            + source_text[sum(len(lines[i]) for i in range(line_idx + 1)):]
        )
        context.original = source_text
        context.suggestion_lines[:] = new_text.splitlines()
        context.full_file_mode = True

    def _apply_replace_bare_except_with_exception(self, node: Any, action: FixAction, context: FixContext) -> None:
        if node.__class__.__name__ != "ExceptHandler":
            return

        if getattr(node, "type", None) is not None:
            return

        source_text = getattr(node.root(), "file_content", "")
        if not source_text:
            return

        lineno = getattr(node, "lineno", None)
        if lineno is None:
            return

        lines = source_text.splitlines(keepends=True)
        line_idx = lineno - 1
        if line_idx < 0 or line_idx >= len(lines):
            return

        line = lines[line_idx]
        new_line = re.sub(r"(^\s*except)(\s*:)", r"\1 Exception\2", line, count=1)

        if new_line == line:
            return

        start = sum(len(lines[i]) for i in range(line_idx))
        end = start + len(line)

        new_text = source_text[:start] + new_line + source_text[end:]

        context.original = source_text
        context.suggestion_lines[:] = new_text.splitlines()
        context.full_file_mode = True

    def _apply_replace_mutable_default_with_none(self, node, action, context):
        default_node = context.refs.get("mutable_default_node")
        if default_node is None:
            return

        self._replace_node_range_in_context(default_node, "None", context)

    def _apply_insert_mutable_default_guard(self, node, action, context):
        arg_name = context.refs.get("mutable_arg_name")
        default_expr = context.refs.get("mutable_default_expr")

        if not arg_name or not default_expr:
            return

        if not context.full_file_mode:
            source_text = getattr(node.root(), "file_content", "")
            if not source_text:
                return
            context.original = source_text
            context.suggestion_lines[:] = source_text.splitlines()
            context.full_file_mode = True

        body = getattr(node, "body", None) or []
        if not body:
            return

        first_stmt = body[0]
        insert_lineno = getattr(first_stmt, "lineno", None)
        if insert_lineno is None:
            return

        if self._is_docstring_stmt(first_stmt):
            insert_lineno = getattr(first_stmt, "end_lineno", insert_lineno) + 1

        indent = getattr(first_stmt, "col_offset", getattr(node, "col_offset", 0) + 4)

        guard_lines = [
            " " * indent + f"if {arg_name} is None:",
            " " * (indent + 4) + f"{arg_name} = {default_expr}",
        ]

        insert_at = max(insert_lineno - 1, 0)
        context.suggestion_lines[insert_at:insert_at] = guard_lines

    def _apply_replace_print_listcomp_with_for_loop(self, node: Any, action: FixAction, context: FixContext) -> None:
        if node.__class__.__name__ != "Expr":
            return

        comp = getattr(node, "value", None)
        if comp is None or comp.__class__.__name__ != "ListComp":
            return

        elt = getattr(comp, "elt", None)
        if elt is None or elt.__class__.__name__ != "Call":
            return

        func = getattr(elt, "func", None)
        func_name = getattr(func, "name", None) or getattr(func, "id", None)
        if func_name != "print":
            return

        generators = getattr(comp, "generators", None) or []
        if len(generators) != 1:
            return

        gen = generators[0]

        try:
            target_text = gen.target.as_string()
            iter_text = gen.iter.as_string()
            elt_text = elt.as_string()
        except Exception:
            return

        base_indent = " " * getattr(node, "col_offset", 0)
        body_indent = base_indent + " " * 4

        lines = [f"{base_indent}for {target_text} in {iter_text}:"]

        ifs = getattr(gen, "ifs", None) or []
        current_indent = body_indent

        for cond in ifs:
            try:
                cond_text = cond.as_string()
            except Exception:
                return
            lines.append(f"{current_indent}if {cond_text}:")
            current_indent += " " * 4

        lines.append(f"{current_indent}{elt_text}")
        context.suggestion_lines[:] = lines

    def _apply_remove_redundant_sorted(self, node, action, context):
        if node.__class__.__name__ != "Call":
            return

        args = getattr(node, "args", [])
        if not args:
            return

        first = args[0]
        if first.__class__.__name__ != "Call":
            return

        func = getattr(first, "func", None)
        if func is None:
            return

        name = getattr(func, "name", None) or getattr(func, "id", None)
        if name != "sorted":
            return

        keywords = getattr(first, "keywords", [])
        if keywords:
            return

        inner_args = getattr(first, "args", [])
        if not inner_args:
            return

        try:
            inner = inner_args[0].as_string()
            func_name = node.func.as_string()
            new = f"{func_name}({inner})"
            context.suggestion_lines[:] = [new]
        except Exception:
            return

    def _apply_replace_join_listcomp_with_generator(self, node, action, context) -> None:
        if node.__class__.__name__ != "Call":
            return

        args = getattr(node, "args", None) or []
        if len(args) != 1:
            return

        first = args[0]
        replacement = None

        if first.__class__.__name__ == "ListComp":
            try:
                text = first.as_string().strip()
            except Exception:
                return

            if text.startswith("[") and text.endswith("]"):
                replacement = text[1:-1]
            else:
                return

        elif first.__class__.__name__ == "Call":
            func = getattr(first, "func", None)
            func_name = None

            if func is not None:
                if func.__class__.__name__ == "Name":
                    func_name = getattr(func, "name", None) or getattr(func, "id", None)
                elif func.__class__.__name__ == "Attribute":
                    func_name = (
                        getattr(func, "attrname", None)
                        or getattr(func, "attr", None)
                        or getattr(func, "name", None)
                    )

            inner_args = getattr(first, "args", None) or []
            if func_name == "list" and len(inner_args) == 1:
                inner = inner_args[0]
                if inner.__class__.__name__ == "GeneratorExp":
                    try:
                        replacement = inner.as_string().strip()
                    except Exception:
                        return

        if not replacement:
            return

        self._replace_node_range_in_context(first, replacement, context)

    def _apply_replace_eval_with_literal_eval(self, node: Any, action: FixAction, context: FixContext) -> None:
        if node.__class__.__name__ != "Call":
            return

        func = getattr(node, "func", None)
        if func is None:
            return

        func_name = getattr(func, "name", None) or getattr(func, "id", None)
        if func_name != "eval":
            return

        source_text = getattr(node.root(), "file_content", "")
        if not source_text:
            return

        lines = source_text.splitlines(keepends=True)

        lineno = getattr(func, "lineno", None)
        col = getattr(func, "col_offset", None)
        end_lineno = getattr(func, "end_lineno", None)
        end_col = getattr(func, "end_col_offset", None)

        if None in (lineno, col, end_lineno, end_col):
            return

        start_offset = sum(len(lines[i]) for i in range(lineno - 1)) + col
        end_offset = sum(len(lines[i]) for i in range(end_lineno - 1)) + end_col

        new_text = source_text[:start_offset] + "ast.literal_eval" + source_text[end_offset:]

        if not re.search(r"^\s*import\s+ast\b|^\s*from\s+ast\s+import\b", new_text, flags=re.MULTILINE):
            new_lines = new_text.splitlines()

            insert_at = 0
            if new_lines and new_lines[0].startswith("#!"):
                insert_at = 1
            if insert_at < len(new_lines) and "coding" in new_lines[insert_at]:
                insert_at += 1

            new_lines.insert(insert_at, "import ast")
            new_text = "\n".join(new_lines)

        context.original = source_text
        context.suggestion_lines[:] = new_text.splitlines()
        context.full_file_mode = True

    def _apply_replace_unnecessary_copy(self, node: Any, action: FixAction, context: FixContext) -> None:
        if node.__class__.__name__ != "Call":
            return

        outer_name = self._get_call_name(node)
        if outer_name not in {"list", "set", "dict", "copy", "deepcopy"}:
            return

        args = getattr(node, "args", []) or []
        keywords = getattr(node, "keywords", []) or []

        if len(args) != 1 or keywords:
            return

        first = args[0]
        first_type = first.__class__.__name__
        replacement = None

        if first_type == "Call":
            inner_name = self._get_call_name(first)
            inner_args = getattr(first, "args", []) or []
            inner_keywords = getattr(first, "keywords", []) or []

            if outer_name in {"list", "set", "dict"} and inner_name == outer_name:
                if len(inner_args) == 1 and not inner_keywords:
                    try:
                        replacement = f"{outer_name}({inner_args[0].as_string().rstrip()})"
                    except Exception:
                        return

        elif outer_name == "list" and first_type in {"List", "ListComp"}:
            try:
                replacement = first.as_string().rstrip()
            except Exception:
                return

        elif outer_name == "set" and first_type in {"Set", "SetComp"}:
            try:
                replacement = first.as_string().rstrip()
            except Exception:
                return

        elif outer_name == "dict" and first_type == "Dict":
            try:
                replacement = first.as_string().rstrip()
            except Exception:
                return

        elif outer_name in {"copy", "deepcopy"} and first_type in {"List", "Set", "Dict", "ListComp", "SetComp"}:
            try:
                replacement = first.as_string().rstrip()
            except Exception:
                return

        if not replacement:
            return

        self._replace_node_range_in_context(node, replacement, context)

    def _apply_ensure_import(self, node: Any, action: FixAction, context: FixContext) -> None:
        module = action.params["module"]

        source_text = self._get_working_text(node, context)
        if not source_text:
            return

        lines = source_text.splitlines()
        if self._has_import(lines, module):
            return

        insert_at = self._find_import_insertion_index(lines)
        lines.insert(insert_at, f"import {module}")

        new_text = "\n".join(lines)
        context.working_text = new_text
        context.suggestion_lines[:] = new_text.splitlines()
        context.full_file_mode = True

    def _apply_replace_os_system_with_subprocess_template(
        self,
        node: Any,
        action: FixAction,
        context: FixContext,
    ) -> None:
        if node.__class__.__name__ != "Call":
            return

        source_text = getattr(node.root(), "file_content", "")
        if not source_text:
            return

        lineno = getattr(node, "lineno", None)
        col = getattr(node, "col_offset", None)
        end_lineno = getattr(node, "end_lineno", None)
        end_col = getattr(node, "end_col_offset", None)

        if None in (lineno, col, end_lineno, end_col):
            return

        lines = source_text.splitlines()

        if not self._has_import(lines, "subprocess"):
            insert_at = self._find_import_insertion_index(lines)
            lines.insert(insert_at, "import subprocess")

            if insert_at + 1 < len(lines) and lines[insert_at + 1].strip() != "":
                lines.insert(insert_at + 1, "")

        line_shift = len(lines) - len(source_text.splitlines())

        new_source = "\n".join(lines)
        new_lines_keepends = [line + "\n" for line in lines[:-1]]
        if lines:
            new_lines_keepends.append(lines[-1])

        adjusted_lineno = lineno + line_shift
        adjusted_end_lineno = end_lineno + line_shift

        if adjusted_lineno - 1 >= len(new_lines_keepends) or adjusted_end_lineno - 1 >= len(new_lines_keepends):
            return

        start_offset = sum(len(new_lines_keepends[i]) for i in range(adjusted_lineno - 1)) + col
        end_offset = sum(len(new_lines_keepends[i]) for i in range(adjusted_end_lineno - 1)) + end_col

        replacement = 'subprocess.run([...], check=True)'
        final_text = new_source[:start_offset] + replacement + new_source[end_offset:]

        context.original = source_text
        context.suggestion_lines[:] = final_text.splitlines()
        context.full_file_mode = True

    def _apply_replace_os_system_with_subprocess_run(
        self,
        node: Any,
        action: FixAction,
        context: FixContext,
    ) -> None:
        if node.__class__.__name__ != "Call":
            return

        func = getattr(node, "func", None)
        if func is None or func.__class__.__name__ != "Attribute":
            return

        base = getattr(func, "expr", None) or getattr(func, "value", None)
        base_name = getattr(base, "name", None) or getattr(base, "id", None)
        attr_name = getattr(func, "attrname", None) or getattr(func, "attr", None)

        if base_name != "os" or attr_name != "system":
            return

        args = getattr(node, "args", None) or []
        keywords = getattr(node, "keywords", None) or []

        if len(args) != 1 or keywords:
            return

        try:
            cmd_text = args[0].as_string().rstrip()
        except Exception:
            return

        replacement = f"subprocess.run({cmd_text}, shell=True, check=True)"
        self._replace_node_range_in_context(node, replacement, context)
