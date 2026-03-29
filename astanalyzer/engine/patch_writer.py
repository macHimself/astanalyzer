from __future__ import annotations

import logging
import re
import textwrap
from datetime import datetime
from pathlib import Path
from colorama import Fore, Style, init
from ..fixer import FixProposal

from .project_loader import ModuleNode
from .reporting import _relpath

log = logging.getLogger(__name__)
init(autoreset=True)


def _slug(s: str, max_len: int = 60) -> str:
    """
    Convert text to a filesystem-safe slug.
    """
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:max_len] or "run"


def make_patch_run_dir(project_root: Path) -> Path:
    """
    Create a directory for patch artefacts under ``.astanalyzer/patches``.
    """
    base = project_root / ".astanalyzer" / "patches"
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = base / f"{ts}__{_slug(project_root.name)}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_patch(
    *,
    patch_run_dir: Path,
    rule_id: str,
    rel_file: str,
    index: int,
    patch_text: str,
) -> Path:
    """
    Write a patch next to the source file.

    ``patch_run_dir`` is currently ignored to preserve old behaviour.
    """
    source_path = Path(rel_file)

    if not source_path.is_absolute():
        source_path = (Path.cwd() / source_path).resolve()
    else:
        source_path = source_path.resolve()

    patch_name = f"{source_path.name}__{rule_id}__{index:04d}.patch"
    out = source_path.with_name(patch_name)
    out.write_text(patch_text, encoding="utf-8")
    return out


def present_foundings_suggestions(fix: FixProposal) -> None:
    """
    Print a formatted debug preview of a proposed fix.
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
    Generate unified diff text for a fix proposal and store it on the object.
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
    rule_title: str,
    project_root: Path,
) -> Path | None:
    if patch_run_dir is None:
        return None

    if not isinstance(fix, FixProposal):
        return None

    if fix.suggestion == fix.original:
        return None

    resolve_fix_line_range(fix, match)

    rel_file = _relpath(
        Path(getattr(fix, "filename", module.filename)),
        project_root,
    )

    return write_patch(
        patch_run_dir=patch_run_dir,
        rule_id=rule_id,
        rel_file=rel_file,
        index=patch_index,
        patch_text=fix.get_diff(),
    )
