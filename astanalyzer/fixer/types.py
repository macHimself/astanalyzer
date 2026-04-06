"""
Data types for fix proposals and fixer execution context.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FixProposal:
    """Concrete proposed source change with unified diff output."""

    original: str
    suggestion: str
    reason: str
    lineno: int = 1
    filename: str = "file.py"
    full_file_mode: bool = False

    def get_diff(self) -> str:
        """Return unified diff for this proposal against the current file on disk."""
        file_path = Path(self.filename)
        full_text = file_path.read_text(encoding="utf-8")

        original_had_no_final_newline = not full_text.endswith("\n")
        full_lines = full_text.splitlines()

        suggestion_text = self.suggestion or ""
        suggestion_lines = suggestion_text.splitlines()

        rel_path = file_path.name

        if self.full_file_mode:
            new_lines = suggestion_lines
        else:
            original_text = self.original or ""
            original_lines = original_text.splitlines()

            start = max(self.lineno - 1, 0)
            end = start + len(original_lines)

            new_lines = full_lines[:start] + suggestion_lines + full_lines[end:]

        diff = list(
            difflib.unified_diff(
                full_lines,
                new_lines,
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
                lineterm="",
                n=3,
            )
        )

        if diff and original_had_no_final_newline:
            return "\n".join(diff) + "\n"

        return "\n".join(diff) + "\n"

    def __str__(self) -> str:
        return f"{self.reason} [{self.original} -> {self.suggestion}]"


@dataclass
class FixAction:
    """Recorded DSL action."""

    kind: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class FixContext:
    """Mutable execution state while building a concrete fix proposal."""

    original: str
    suggestion_lines: list[str]
    delete_entirely: bool = False
    full_file_mode: bool = False
    refs: dict[str, Any] = field(default_factory=dict)
    working_text: str | None = None


@dataclass
class TextReplacement:
    """Simple text replacement descriptor."""

    line: int
    old: str
    new: str
