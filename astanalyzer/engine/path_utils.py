"""Path resolution helpers shared by scan reporting and patch generation."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def normalize_project_root(project_root: str | Path | None) -> Path | None:
    """Return the resolved project root when provided."""
    if project_root in (None, ""):
        return None
    return Path(project_root).expanduser().resolve()


def resolve_report_file_path(
    file_value: str | Path,
    *,
    project_root: str | Path | None = None,
    report_base_dir: str | Path | None = None,
) -> Path:
    """Resolve a file path from scan JSON into an absolute filesystem path.

    Relative paths are interpreted against the project root first, then against
    the report file directory, and finally against the current working
    directory.
    """
    path = Path(file_value).expanduser()
    if path.is_absolute():
        return path.resolve()

    root = normalize_project_root(project_root)
    if root is not None:
        return (root / path).resolve()

    if report_base_dir is not None:
        return (Path(report_base_dir).expanduser().resolve() / path).resolve()

    return path.resolve()


def to_project_relative_path(path: str | Path, *, project_root: str | Path | None) -> str:
    """Convert a path to project-relative POSIX form when possible."""
    resolved = Path(path).expanduser().resolve()
    root = normalize_project_root(project_root)

    if root is not None:
        try:
            return resolved.relative_to(root).as_posix()
        except ValueError:
            pass

    return resolved.as_posix()


def extract_file_value(item: dict[str, Any]) -> str | None:
    """Extract file path from a finding or selected action.

    Preference order:
    1. top-level ``file``
    2. ``anchor.file``

    Returns ``None`` when no usable file path is present.
    """
    file_value = item.get("file")
    if isinstance(file_value, str) and file_value.strip():
        return file_value

    anchor = item.get("anchor")
    if isinstance(anchor, dict):
        anchor_file = anchor.get("file")
        if isinstance(anchor_file, str) and anchor_file.strip():
            return anchor_file

    return None
