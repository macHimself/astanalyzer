"""Selected JSON resolution helpers for patch and archive commands."""

from __future__ import annotations

import json
import logging
import shutil
import sys
from pathlib import Path

from ...engine import normalize_project_root

log = logging.getLogger(__name__)

def read_project_root_from_selected_json(selected_path: Path | None = None) -> Path | None:
    """Read project_root from selected JSON if available."""
    candidates: list[Path] = []

    if selected_path is not None:
        candidates.append(selected_path)

    cwd = Path.cwd()
    candidates.extend([
        cwd / "astanalyzer-selected.json",
        cwd / "selected.json",
    ])

    for candidate in candidates:
        if not candidate.exists() or not candidate.is_file():
            continue

        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        project_root = normalize_project_root(data.get("project_root"))
        if project_root is not None:
            return project_root

    return None


def resolve_selected_input(
    selected_arg: str | None = None,
    *,
    copy_from_downloads: bool = True,
    required: bool = True,
) -> Path | None:
    """
    Resolve the selected findings JSON file from multiple possible sources.

    The resolution follows this priority:
        1. Explicit CLI path (if provided)
        2. Working directory ('astanalyzer-selected.json' or 'selected.json')
        3. Newest matching file in '~/Downloads' ('astanalyzer-selected*.json')

    If a resolved file is outside the current working directory and
    `copy_from_downloads` is enabled, it is copied into the current working
    directory and removed from its original location. This also applies to an
    explicit path such as '~/Downloads/astanalyzer-selected.json'.

    Args:
        selected_arg (str | None): Optional explicit path to the selected JSON file.
        copy_from_downloads (bool): If True, copy the resolved file into
            the working directory and delete the original when it is outside
            the working directory. If False, use the file in-place. Defaults
            to True.
        required (bool): If True, terminate the command when no selected JSON
            can be resolved. If False, return None when no fallback file exists.

    Returns:
        Path | None: Path to the resolved selected JSON file, or None when
        `required` is False and no file is found.

    Raises:
        SystemExit: If no valid selected JSON file is found and `required` is
        True, or if the provided path is invalid.

    Side Effects:
        - May copy a file into the working directory.
        - May overwrite an existing file in the working directory.
        - May delete the original file after a successful copy.
        - Emits log messages describing resolution steps.

    Notes:
        - Files are selected from Downloads based on the most recent modification time.
        - The function prefers local files over Downloads when no explicit path is provided.
    """
    cwd = Path.cwd().resolve()

    if selected_arg:
        p = Path(selected_arg).expanduser().resolve()
        if not p.exists():
            log.error("Selected file '%s' doesn't exist.", p)
            sys.exit(1)
        if not p.is_file():
            log.error("Selected path '%s' is not a file.", p)
            sys.exit(1)

        target = (cwd / p.name).resolve()

        if copy_from_downloads and p != target:
            if target.exists():
                log.warning("Overwriting existing file in working directory: %s", target)

            shutil.copy2(p, target)
            if p.exists():
                p.unlink()

            log.info("Moved selected JSON into working directory: %s -> %s", p, target)
            return target

        return p

    local_candidates = [
        cwd / "astanalyzer-selected.json",
        cwd / "selected.json",
    ]
    for candidate in local_candidates:
        if candidate.exists() and candidate.is_file():
            log.info("Using selected JSON from working directory: %s", candidate)
            return candidate.resolve()

    downloads = Path.home() / "Downloads"
    if not downloads.exists() or not downloads.is_dir():
        if not required:
            return None
        log.error(
            "Downloads directory '%s' does not exist and no local selected JSON was found.",
            downloads,
        )
        sys.exit(1)

    candidates = sorted(
        downloads.glob("astanalyzer-selected*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not candidates:
        if not required:
            return None
        log.error(
            "No selected JSON found in working directory or Downloads "
            "(looked for 'astanalyzer-selected.json', 'selected.json', "
            "and '~/Downloads/astanalyzer-selected*.json')."
        )
        sys.exit(1)

    newest = candidates[0].resolve()

    if not copy_from_downloads:
        log.info("Using selected JSON directly from Downloads: %s", newest)
        return newest

    target = (cwd / newest.name).resolve()

    if target.exists():
        try:
            same_file = target.resolve() == newest.resolve()
        except FileNotFoundError:
            same_file = False

        if same_file:
            log.info("Selected JSON already available in working directory: %s", target)
            return target

        log.warning("Overwriting existing file in working directory: %s", target)

    shutil.copy2(newest, target)
    if newest.exists():
        newest.unlink()

    log.info("Copied selected JSON from Downloads: %s -> %s", newest, target)
    return target.resolve()


def resolve_selected_cli_argument(
    positional_path: str | None,
    deprecated_selected_path: str | None,
) -> str | None:
    """Resolve mutually exclusive CLI inputs for selected JSON commands."""
    if positional_path and deprecated_selected_path:
        log.error(
            "Use either the positional selected JSON path or --selected, not both."
        )
        sys.exit(2)

    if deprecated_selected_path:
        log.warning(
            "--selected is deprecated; use the positional selected_json_path argument instead."
        )
        return deprecated_selected_path

    return positional_path
