"""File and path helpers used by CLI commands."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from ...engine import extract_file_value, normalize_project_root, resolve_report_file_path

log = logging.getLogger(__name__)

def ensure_final_newline(path: Path) -> None:
    """
    Ensure that the given file ends with a newline character.

    If the file does not already end with a newline ('\\n'), one is appended.
    If the file already ends with a newline, no changes are made.

    Args:
        path (Path): Path to the file to be checked and potentially modified.

    Side Effects:
        - Reads the entire file content into memory.
        - Rewrites the file if a newline needs to be appended.

    Notes:
        - Uses UTF-8 encoding for reading and writing.
        - This helps ensure compatibility with tools such as `git diff`
          and patch application, which may expect a trailing newline.
    """
    text = path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        path.write_text(text + "\n", encoding="utf-8")


def collect_selected_files(
    selected_data: dict[str, Any],
    base_dir: Path | None = None,
    project_root: Path | None = None,
) -> list[Path]:
    """
    Extract and normalize unique file paths from selected findings data.

    The function iterates over the 'findings' section of the provided data,
    collects file paths, resolves them to absolute paths, and removes duplicates
    while preserving the original order.

    Args:
        selected_data (dict[str, Any]): Parsed selected JSON containing findings.
        base_dir (Path | None): Base directory used to resolve relative paths.
            If provided, relative paths are resolved against this directory.
            Otherwise, paths are resolved relative to the current working directory.

    Returns:
        list[Path]: List of unique, resolved file paths referenced in the findings.

    Notes:
        - Entries without a 'file' field are ignored.
        - If 'findings' is missing or not a list, an empty list is returned.
        - Duplicate file paths are removed while preserving insertion order.
    """
    files: list[Path] = []
    seen: set[Path] = set()

    findings = selected_data.get("findings", []) or [] 
    if not isinstance(findings, list):
        return files

    selected_actions = selected_data.get("selected_actions", []) or []
    
    effective_project_root = normalize_project_root(project_root) or normalize_project_root(selected_data.get("project_root"))

    for item in [*findings, *selected_actions]:
        file_value = extract_file_value(item)
        if not file_value:
            continue

        p = resolve_report_file_path(
            file_value,
            project_root=effective_project_root,
            report_base_dir=base_dir,
        )

        if p not in seen:
            seen.add(p)
            files.append(p)

    return files


def validate_path(str_path: str) -> Path:
    """
    Validate that the given path exists and return it as a Path object.

    If the path does not exist, the function logs an error message and
    terminates the program with a non-zero exit code.

    Args:
        str_path (str): Input path provided as a string.

    Returns:
        Path: Path object if the path exists.
    #Path: Resolved Path object if the path exists.
    

    Raises:
        SystemExit: If the path does not exist.

    Side Effects:
        - Logs an error message when the path is invalid.
        - Terminates the process using sys.exit(1).
    """

    path = Path(str_path).expanduser().resolve()
    if not path.exists():
        log.error("Path '%s' doesn't exist.", path)
        sys.exit(1)

    log.info("Existing path: %s", path)
    return path
