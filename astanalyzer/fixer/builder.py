"""
Public fixer DSL builder.
"""

from __future__ import annotations

from typing import Any, Callable

from .actions import FixerActionsMixin
from .types import FixAction, FixContext, FixProposal


class ProposalBuilder:
    """Common base class for code-change proposal builders."""

    def __init__(self, title: str = "Proposed change") -> None:
        self.title = title
        self.reason_parts: list[str] = []

    def because(self, reason: str):
        """Append a human-readable reason fragment."""
        if reason:
            self.reason_parts.append(reason)
        return self

    def reason_text(self) -> str:
        return "; ".join(self.reason_parts) or "reason not given"

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "reason": self.reason_text(),
            "dsl": {
                "because": self.reason_text(),
                "actions": self._actions_for_dict(),
            },
        }

    def _actions_for_dict(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def build(self, node: Any, module=None, project=None, project_root=None):
        raise NotImplementedError


class FixerBuilder(ProposalBuilder, FixerActionsMixin):
    """Chainable DSL for building concrete local fix proposals."""

    def __init__(self) -> None:
        super().__init__(title="Proposed fix")
        self.actions: list[FixAction] = []
        self.custom_actions: list[tuple[Callable[..., None], dict[str, Any]]] = []

    def _actions_for_dict(self) -> list[dict[str, Any]]:
        actions = []

        for action in self.actions:
            if hasattr(action, "kind") and hasattr(action, "params"):
                actions.append({"op": action.kind, **action.params})
            elif isinstance(action, tuple) and action:
                actions.append({"op": action[0]})
            else:
                actions.append({"op": str(action)})

        if self.custom_actions:
            actions.append({"op": "custom", "count": len(self.custom_actions)})

        return actions

    def insert_before(self, text: str, indent: int = 0, comment: str | None = None) -> "FixerBuilder":
        self._validate_single_line(text, "insert_before")
        self.actions.append(FixAction("insert_before", {"text": text, "indent": indent, "comment": comment}))
        return self

    def insert_after(self, text: str, indent: int = 0, comment: str | None = None) -> "FixerBuilder":
        self._validate_single_line(text, "insert_after")
        self.actions.append(FixAction("insert_after", {"text": text, "indent": indent, "comment": comment}))
        return self

    def append(self, text: str, indent: int = 0, comment: str | None = None) -> "FixerBuilder":
        self._validate_single_line(text, "append")
        self.actions.append(FixAction("append", {"text": text, "indent": indent, "comment": comment}))
        return self

    def prepend(self, text: str, indent: int = 0, comment: str | None = None) -> "FixerBuilder":
        self._validate_single_line(text, "prepend")
        self.actions.append(FixAction("prepend", {"text": text, "indent": indent, "comment": comment}))
        return self

    def replace_with(self, text: str) -> "FixerBuilder":
        self.actions.append(FixAction("replace_with", {"text": text}))
        return self

    def replace_line(self, text: str, indent: int = 0, comment: str | None = None) -> "FixerBuilder":
        self._validate_single_line(text, "replace_line")
        self.actions.append(FixAction("replace_line", {"text": text, "indent": indent, "comment": comment}))
        return self

    def insert_at_body_start(self, text: str, comment: str | None = None) -> "FixerBuilder":
        self._validate_single_line(text, "insert_at_body_start")
        self.actions.append(FixAction("insert_at_body_start", {"text": text, "comment": comment}))
        return self

    def comment_before(self, text: str) -> "FixerBuilder":
        self.actions.append(FixAction("comment_before", {"text": text}))
        return self

    def comment_after(self, text: str) -> "FixerBuilder":
        self.actions.append(FixAction("comment_after", {"text": text}))
        return self

    def add_docstring(self, text: str = '"""TODO: Add docstring."""') -> "FixerBuilder":
        self.actions.append(FixAction("add_docstring", {"text": text}))
        return self

    def comment_on_function(self, text: str) -> "FixerBuilder":
        self.actions.append(FixAction("comment_on_function", {"text": text}))
        return self

    def remove_line(self) -> "FixerBuilder":
        self.actions.append(FixAction("remove_line"))
        return self

    def remove_statement(self) -> "FixerBuilder":
        self.actions.append(FixAction("delete_node"))
        return self

    def delete_node(self) -> "FixerBuilder":
        self.actions.append(FixAction("delete_node"))
        return self

    def remove_dead_code_after(self) -> "FixerBuilder":
        self.actions.append(FixAction("remove_dead_code_after"))
        return self

    def remove_orelse_header(self) -> "FixerBuilder":
        self.actions.append(FixAction("remove_orelse_header"))
        return self

    def unindent_orelse(self, spaces: int = 4) -> "FixerBuilder":
        self.actions.append(FixAction("unindent_orelse", {"spaces": spaces}))
        return self

    def remove_block_header(self, attr: str) -> "FixerBuilder":
        self.actions.append(FixAction("remove_block_header", {"attr": attr}))
        return self

    def unindent_block(self, attr: str, spaces: int = 4) -> "FixerBuilder":
        self.actions.append(FixAction("unindent_block", {"attr": attr, "spaces": spaces}))
        return self

    def strip_trailing_whitespace(self) -> "FixerBuilder":
        self.actions.append(FixAction("strip_trailing_whitespace"))
        return self

    def insert_blank_line_before(self) -> "FixerBuilder":
        self.actions.append(FixAction("insert_blank_line_before"))
        return self

    def add_module_docstring(self, text: str = '"""TODO: Add module docstring."""') -> "FixerBuilder":
        self.actions.append(FixAction("add_module_docstring", {"text": text}))
        return self

    def replace_with_value(self) -> "FixerBuilder":
        self.actions.append(FixAction("replace_with_value"))
        return self

    def flatten_always_true_if(self) -> "FixerBuilder":
        self.actions.append(FixAction("flatten_always_true_if"))
        return self

    def replace_none_comparison_operator(self) -> "FixerBuilder":
        self.actions.append(FixAction("replace_none_comparison_operator"))
        return self

    def replace_range(self, text: str) -> "FixerBuilder":
        self.actions.append(FixAction("replace_range", {"text": text}))
        return self

    def replace_node_text(self, text: str) -> "FixerBuilder":
        self.actions.append(FixAction("replace_node_text", {"text": text}))
        return self

    def remove_node(self, ref: str):
        self.actions.append(FixAction("remove_node", {"ref": ref}))
        return self

    def remove_except_alias(self) -> "FixerBuilder":
        self.actions.append(FixAction("remove_except_alias"))
        return self

    def replace_bare_except_with_exception(self) -> "FixerBuilder":
        self.actions.append(FixAction("replace_bare_except_with_exception"))
        return self

    def replace_mutable_default_with_none(self) -> "FixerBuilder":
        self.actions.append(FixAction("replace_mutable_default_with_none"))
        return self

    def insert_mutable_default_guard(self) -> "FixerBuilder":
        self.actions.append(FixAction("insert_mutable_default_guard"))
        return self

    def replace_print_listcomp_with_for_loop(self) -> "FixerBuilder":
        self.actions.append(FixAction("replace_print_listcomp_with_for_loop"))
        return self

    def remove_redundant_sorted(self) -> "FixerBuilder":
        self.actions.append(FixAction("remove_redundant_sorted"))
        return self

    def replace_unnecessary_copy(self) -> "FixerBuilder":
        self.actions.append(FixAction("replace_unnecessary_copy"))
        return self

    def replace_join_listcomp_with_generator(self) -> "FixerBuilder":
        self.actions.append(FixAction("replace_join_listcomp_with_generator"))
        return self

    def replace_eval_with_literal_eval(self) -> "FixerBuilder":
        self.actions.append(FixAction("replace_eval_with_literal_eval"))
        return self

    def ensure_import(self, module: str) -> "FixerBuilder":
        self.actions.append(FixAction("ensure_import", {"module": module}))
        return self

    def replace_os_system_with_subprocess_template(self) -> "FixerBuilder":
        self.actions.append(FixAction("replace_os_system_with_subprocess_template"))
        return self

    def replace_os_system_with_subprocess_run(self) -> "FixerBuilder":
        self.actions.append(FixAction("replace_os_system_with_subprocess_run"))
        return self

    def custom(self, fn: Callable[..., None], **kwargs: Any) -> "FixerBuilder":
        self.custom_actions.append((fn, kwargs))
        return self

    def build(self, node: Any, module=None, project=None, project_root=None, refs=None) -> FixProposal:
        original = self._get_original_source(node)
        context = FixContext(
            original=original,
            suggestion_lines=original.splitlines(),
            refs=refs or {},
            working_text=None,
        )

        for action in self.actions:
            self._apply_action(node, action, context)

        for fn, kwargs in self.custom_actions:
            fn(node, context.suggestion_lines, context, **kwargs)

        suggestion = "" if context.delete_entirely else "\n".join(context.suggestion_lines)
        proposal_lineno = 1 if context.full_file_mode else getattr(node, "lineno", 1)

        return FixProposal(
            original=context.original,
            suggestion=suggestion,
            reason="; ".join(self.reason_parts) or "reason not given",
            lineno=proposal_lineno,
            filename=str(getattr(node.root(), "file", "unknown.py")),
            full_file_mode=context.full_file_mode,
        )

    def insert_comment(self, text_builder):
        """Backward-compatible alias for dynamic or static comment insertion."""
        def _apply(node, suggestion_lines, context, **kwargs):
            indent = " " * getattr(node, "col_offset", 0)

            text = text_builder(node) if callable(text_builder) else text_builder
            if not text:
                return

            if not text.lstrip().startswith("#"):
                text = f"# {text}"

            suggestion_lines.insert(0, f"{indent}{text}")

        self.custom_actions.append((_apply, {}))
        return self

    def __str__(self) -> str:
        actions = []
        for action in self.actions:
            if action.params:
                args = ", ".join(f"{k}={v!r}" for k, v in action.params.items())
                actions.append(f"{action.kind}({args})")
            else:
                actions.append(action.kind)
        reason = "; ".join(self.reason_parts) or "no reason given"
        return " -> ".join(actions) + f' because "{reason}"'


def fix() -> FixerBuilder:
    """Create a new FixerBuilder."""
    return FixerBuilder()