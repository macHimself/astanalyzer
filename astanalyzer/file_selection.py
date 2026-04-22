from __future__ import annotations

from pathlib import Path


def parse_excluded_dir_names(raw: str | None) -> set[str]:
    """
    Parse a comma-separated list of directory names to exclude from scan.
    """
    if raw is None:
        return set()

    items = {item.strip() for item in raw.split(",")}
    return {item for item in items if item}


def should_skip_path(path: Path, excluded_dir_names: set[str]) -> bool:
    """
    Return True if the path is located inside a directory whose name is excluded.

    Example:
    - excluded_dir_names = {"tests"}
    - src/tests/test_x.py -> skipped
    - tests/unit/test_x.py -> skipped
    - src/testing/foo.py -> not skipped
    """
    if not excluded_dir_names:
        return False

    return any(part in excluded_dir_names for part in path.parts)


def filter_scan_paths(paths: list[Path], excluded_dir_names: set[str]) -> list[Path]:
    """
    Filter discovered scan paths according to excluded directory names.
    """
    return [
        path for path in paths
        if not should_skip_path(path, excluded_dir_names)
    ]