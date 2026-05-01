"""
Patch generation and diff presentation helpers.

This module provides small utilities for:
- creating patch output directories
- writing generated patch files
- formatting and logging fix previews
- generating and colouring unified diffs
- emitting patch files only when a fix changes the source

These helpers are primarily used by the patch-building workflow and debugging output.
"""
from __future__ import annotations

import logging
import re
import textwrap
from pathlib import Path
from colorama import Fore, Style, init
from ..fixer import FixProposal

from .project_loader import ModuleNode

log = logging.getLogger(__name__)
init(autoreset=True)


def write_patch(
    *,
    patch_run_dir: Path,
    rule_id: str,
    source_path: Path,
    index: int,
    patch_text: str,
) -> Path:
    """
    Write a generated patch file next to the affected source file.

    The patch filename is derived from the source filename, rule identifier,
    and patch index. 
    """
    source_path = Path(source_path).resolve()

    patch_name = f"{source_path.name}__{rule_id}__{index:04d}.patch"
    out = source_path.with_name(patch_name)
    out.write_text(patch_text, encoding="utf-8")
    return out


def present_foundings_suggestions(fix: FixProposal) -> None:
    """
    Log a formatted preview of a proposed fix when debug logging is enabled.

    The preview includes suggested replacement lines and the human-readable
    reason associated with the fix proposal.
    """
    if log.isEnabledFor(logging.DEBUG):
        lines = []

        lines.append("Suggested Fix:")
        lines.append("-" * 60)

        for i, line in enumerate(fix.suggestion.splitlines()):
            lineno_str = str(fix.lineno + i).rjust(4)
            lines.append(f" {lineno_str} | {line}")

        lines.append("-" * 60)
        lines.append("Reason:")
        lines.append(textwrap.fill(fix.reason, width=70))
        lines.append("-" * 60)

        log.debug("\n".join(lines))


def _format_colored_diff(diff_text: str) -> str:
    """
    Apply ANSI colours to unified diff text for terminal-friendly output.

    Added lines are coloured green, removed lines red, and hunk headers cyan.
    """
    lines: list[str] = []

    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            lines.append(Fore.GREEN + line + Style.RESET_ALL)
        elif line.startswith("-") and not line.startswith("---"):
            lines.append(Fore.RED + line + Style.RESET_ALL)
        elif line.startswith("@@"):
            lines.append(Fore.CYAN + line + Style.RESET_ALL)
        else:
            lines.append(line)

    return "\n".join(lines)


def create_diff(fix: FixProposal) -> None:
    """
    Generate unified diff text for a fix proposal and attach it to the object.

    The generated diff is also logged in colourized form at debug level.
    """
    diff_text = fix.get_diff()
    fix.diff = diff_text

    log.debug(
        "DIFF for %s:%s\n%s",
        fix.filename,
        fix.lineno,
        _format_colored_diff(diff_text),
    )

def resolve_fix_line_range(fix, match) -> tuple[int, int]:
    """
    Resolve the effective start and end line range for a fix proposal.

    Missing line information is filled from the matched node. For empty 
    suggestions, multi-line ranges are collapsed to a single line 
    when appropriate.
    """
    sline = getattr(fix, "lineno", None)
    eline = getattr(fix, "end_lineno", None)

    if sline is None:
        sline = getattr(match, "lineno", 1)
    if eline is None:
        eline = getattr(match, "end_lineno", sline)

    if getattr(fix, "suggestion", "") in ("", None) and eline > sline:
        eline = sline

    return sline, eline


def emit_patch_if_changed(
    *,
    fix: FixProposal,
    match,
    module: ModuleNode,
    patch_run_dir: Path | None,
    patch_index: int,
    rule_id: str,
    project_root: Path,
) -> Path | None:
    """
    Write a patch file for a fix proposal only if it produces a real change.

    The function skips patch emission when patch output is disabled, the object
    is not a `FixProposal`, or the suggested text is identical to the original.
    When a change exists, a unified diff is generated and written as a patch file.

    Returns:
        Path | None: Path to the written patch file, or None if no patch was emitted.
    """
    if patch_run_dir is None:
        return None

    if not isinstance(fix, FixProposal):
        return None

    if fix.suggestion == fix.original:
        return None

    source_path = Path(getattr(fix, "filename", module.filename)).resolve()

    return write_patch(
        patch_run_dir=patch_run_dir,
        rule_id=rule_id,
        source_path=source_path,
        index=patch_index,
        patch_text=fix.get_diff(),
    )


def build_patch_preview_data(fixes: list[FixProposal]) -> dict[str, str]:
    """
    Build report-friendly patch preview metadata for one fixer result.

    The preview is a lightweight side artifact for the static HTML report.
    When no concrete diff can be produced, the returned payload explains why.
    """
    if not fixes:
        return {
            "patch_preview": "",
            "patch_preview_status": "unavailable",
            "patch_preview_error": "No concrete fix proposal was produced.",
        }

    preview_chunks: list[str] = []

    for fix in fixes:
        if not isinstance(fix, FixProposal):
            return {
                "patch_preview": "",
                "patch_preview_status": "unavailable",
                "patch_preview_error": f"Unsupported fix result type: {type(fix).__name__}.",
            }

        if fix.suggestion == fix.original:
            continue

        diff_text = fix.get_diff()
        if diff_text.strip():
            preview_chunks.append(diff_text.rstrip())

    if not preview_chunks:
        return {
            "patch_preview": "",
            "patch_preview_status": "unavailable",
            "patch_preview_error": "Preview is not available because the fix would not change the source.",
        }

    preview = "\n\n".join(preview_chunks) + "\n"
    max_chars = 20000
    if len(preview) > max_chars:
        preview = preview[:max_chars] + "\n... truncated ...\n"

    return {
        "patch_preview": preview,
        "patch_preview_status": "available",
    }
