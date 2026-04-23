#!/usr/bin/env python3
"""
Command-line interface for astanalyzer.

This module defines the CLI entry point, command handlers, and supporting
helpers for scanning projects, generating patch files, validating and
applying patches, opening reports, and cleaning or archiving generated
artifacts.

The implementation is intentionally split into:
- small filesystem and patch-management helpers,
- command handlers for individual CLI actions,
- parser construction and application startup logic.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .engine import (
    build_patches_from_selected_json,
    get_list_of_files_in_project,
    load_project,
    run_rules_on_project_report,
    normalize_project_root, 
    resolve_report_file_path, 
    extract_file_value
)
from .file_selection import parse_excluded_dir_names
from .rule import Rule
from .rule_filtering import (
    RuleFilterError,
    build_rule_selection,
    filter_rules,
)
from .logging_config import setup_logging
from .report_ui import open_report_in_browser, write_report_html
from .rule_loader import import_rules_from_path
from .rules import load_builtin_rules

log = logging.getLogger(__name__)

ARCHIVE_DIR_NAME = "used_patches"


def now_stamp() -> str:
    """Return current UTC timestamp formatted as 'YYYY-MM-DD_HH-MM-SS'."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")


def print_section(title: str) -> None:
    """Print a formatted section header for CLI output."""
    print()
    print("=" * 60)
    print(title)

def print_kv(key: str, value: Any) -> None:
    """Print a key–value pair aligned for CLI output."""
    print(f"{key:<20} {value}")


def get_archive_root_path(base_dir: Path | None = None) -> Path:
    """Return the archive directory path without creating it."""
    root = base_dir or Path.cwd()
    return root / ARCHIVE_DIR_NAME


def ensure_archive_root(base_dir: Path | None = None) -> Path:
    """Ensure the archive directory exists and return its path."""
    path = get_archive_root_path(base_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def find_patch_files(
    root: Path | None = None,
    *,
    include_archive: bool = False,
) -> list[Path]:
    """Recursively find all .patch files under the given root directory."""
    search_root = root or Path.cwd()
    archive_root = get_archive_root_path(search_root)

    patch_files: list[Path] = []
    for p in search_root.rglob("*.patch"):
        if not p.is_file():
            continue
        if not include_archive and archive_root in p.parents:
            continue
        patch_files.append(p)

    return sorted(patch_files)


def create_run_archive_dir(base_dir: Path | None = None) -> Path:
    """
    Create a new timestamped archive directory for a single analysis run.

    The directory is created inside the archive root directory and is named
    using the current timestamp in 'YYYY-MM-DD_HH-MM-SS' format.
    This ensures that each run has a unique, chronologically sortable location
    for storing generated patches or related artifacts.

    Args:
        base_dir (Path | None): Optional base directory. Defaults to the current working directory.

    Returns:
        Path: Path to the newly created run-specific archive directory.

    Side Effects:
        Creates the archive root directory (if needed) and a new timestamped subdirectory.
    """
    archive_root = ensure_archive_root(base_dir)
    archive_dir = archive_root / now_stamp()
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir


def move_file_if_exists(src: Path, dst_dir: Path) -> Path | None:
    """
    Move a file to a destination directory if it exists.

    If the source path does not exist or is not a regular file, the function
    returns None and performs no action. Otherwise, the file is moved into
    the specified destination directory using its original filename.

    Args:
        src (Path): Path to the source file.
        dst_dir (Path): Target directory where the file should be moved.

    Returns:
        Path | None: Path to the moved file in the destination directory,
        or None if the source file does not exist or is not a file.

    Side Effects:
        - Moves (renames) the file on the filesystem.
        - Emits a log entry describing the move operation.

    Notes:
        - Existing files in the destination directory may be overwritten,
          depending on the underlying filesystem behavior.
        - The operation uses `Path.rename`, which may fail across different
          filesystems.
    """
    if not src.exists() or not src.is_file():
        return None

    dst = dst_dir / src.name
    src.rename(dst)
    log.info("Archived: %s -> %s", src, dst)
    return dst


def archive_run_artifacts(archive_dir: Path, base_dir: Path | None = None) -> list[Path]:
    """
    Archive known analysis output files into a run-specific archive directory.

    This function looks for a predefined set of artifact files (e.g. scan reports,
    selected fixes, HTML reports) in the given base directory and moves any that
    exist into the provided archive directory.

    The operation is best-effort: only existing files are moved, and missing files
    are silently skipped.

    Args:
        archive_dir (Path): Target directory where artifacts will be stored.
        base_dir (Path | None): Directory to search for artifacts. Defaults to the
            current working directory.

    Returns:
        list[Path]: List of paths to successfully archived files.

    Side Effects:
        - Moves files from the base directory into the archive directory.
        - Emits log messages via `move_file_if_exists`.

    Notes:
        The following filenames are considered:
        - astanalyzer-selected.json
        - selected.json
        - scan_report.json
        - report.html
    """
    root = base_dir or Path.cwd()
    archived: list[Path] = []

    candidates = [
        root / "astanalyzer-selected.json",
        root / "selected.json",
        root / "scan_report.json",
        root / "report.html",
    ]

    for p in candidates:
        out = move_file_if_exists(p, archive_dir)
        if out is not None:
            archived.append(out)

    return archived


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


def archive_patch_files_from_root(archive_dir: Path, base_dir: Path | None = None) -> int:
    """
    Archive all patch files from the project directory into a structured archive location.

    This function searches for all '.patch' files under the base directory (or current
    working directory if not provided) and moves them into a dedicated 'patches'
    subdirectory inside the given archive directory.

    The original directory structure is preserved relative to the base directory,
    ensuring that patch files remain organized according to their source locations.

    Args:
        archive_dir (Path): Target archive directory for the current run.
        base_dir (Path | None): Root directory used to compute relative paths.
            Defaults to the current working directory.

    Returns:
        int: Number of patch files successfully archived.

    Side Effects:
        - Moves patch files from their original locations to the archive directory.
        - Creates intermediate directories as needed.
        - Emits log messages for each moved file.

    Notes:
        - If no patch files are found, the function returns 0 without creating
          the 'patches' directory.
        - The function relies on `find_patch_files`, which scans the
          current working directory recursively.
    """
    root = base_dir or Path.cwd()
    patch_files = find_patch_files(root, include_archive=False)

    if not patch_files:
        return 0

    patches_root = archive_dir / "patches"
    moved = 0

    for patch in patch_files:
        rel_patch = patch.relative_to(root)
        dst = patches_root / rel_patch
        dst.parent.mkdir(parents=True, exist_ok=True)
        patch.rename(dst)
        moved += 1
        log.info("Archived patch: %s -> %s", patch, dst)

    return moved


def has_working_artifacts(base_dir: Path | None = None) -> bool:
    """
    Return True if there are generated artifacts or patch files to archive.
    """
    root = base_dir or Path.cwd()

    candidates = [
        root / "astanalyzer-selected.json",
        root / "selected.json",
        root / "scan_report.json",
        root / "report.html",
    ]

    if any(p.exists() and p.is_file() for p in candidates):
        return True

    return bool(find_patch_files(root, include_archive=False))


def clean_working_artifacts(
    include_archive: bool = False,
    base_dir: Path | None = None,
) -> tuple[int, list[Path]]:
    """
    Remove generated analysis artifacts and patch files from the working directory.

    The function deletes known output files (JSON reports and HTML report) and
    all '.patch' files found recursively under the selected root directory.
    Patch files located inside the archive directory are preserved by default.

    Args:
        include_archive (bool): If True, also delete the archive directory
            ('used_patches') including all its contents. Defaults to False.
        base_dir (Path | None): Root directory to clean. If not provided,
            the current working directory is used.

    Returns:
        tuple[int, list[Path]]:
            - Total number of removed items
            - List of paths that were removed

    Side Effects:
        - Permanently deletes files from the filesystem.
        - Recursively deletes the archive directory if requested.
        - Emits debug log messages describing the cleanup process.

    Notes:
        - The following files are removed if present:
            * astanalyzer-selected.json
            * selected.json
            * scan_report.json
            * report.html
        - All '.patch' files under the root directory are removed.
        - Patch files inside the archive directory are skipped unless
          `include_archive=True`.
    """
    root = base_dir or Path.cwd()
    removed = 0
    removed_paths: list[Path] = []

    log.debug("Starting clean in: %s", root)

    archive_root = get_archive_root_path(root)

    normal_files = [
        root / "astanalyzer-selected.json",
        root / "selected.json",
        root / "scan_report.json",
        root / "report.html",
    ]

    for p in normal_files:
        if p.exists() and p.is_file():
            log.debug("Removing file: %s", p)
            p.unlink()
            removed += 1
            removed_paths.append(p)
        else:
            log.debug("Skipping (not found): %s", p)

    for patch in root.rglob("*.patch"):
        if not patch.is_file():
            continue

        if not include_archive and archive_root in patch.parents:
            log.debug("Skipping archived patch: %s", patch)
            continue

        log.debug("Removing patch: %s", patch)
        patch.unlink()
        removed += 1
        removed_paths.append(patch)

    if include_archive:
        if archive_root.exists() and archive_root.is_dir():
            log.debug("Removing archive directory: %s", archive_root)
            shutil.rmtree(archive_root)
            removed += 1
            removed_paths.append(archive_root)
        else:
            log.debug("No archive directory found: %s", archive_root)

    return removed, removed_paths


def resolve_selected_input(
    selected_arg: str | None = None,
    *,
    copy_from_downloads: bool = True,
) -> Path:
    """
    Resolve the selected findings JSON file from multiple possible sources.

    The resolution follows this priority:
        1. Explicit CLI path (if provided)
        2. Working directory ('selected.json' or 'astanalyzer-selected.json')
        3. Newest matching file in '~/Downloads' ('astanalyzer-selected*.json')

    If a file is found in the Downloads directory and `copy_from_downloads`
    is enabled, it is copied into the current working directory and removed
    from Downloads.

    Args:
        selected_arg (str | None): Optional explicit path to the selected JSON file.
        copy_from_downloads (bool): If True, copy the file from Downloads into
            the working directory and delete the original. If False, use the file
            in-place. Defaults to True.

    Returns:
        Path: Path to the resolved selected JSON file.

    Raises:
        SystemExit: If no valid selected JSON file is found or if the provided
        path is invalid.

    Side Effects:
        - May copy a file from '~/Downloads' to the working directory.
        - May overwrite an existing file in the working directory.
        - May delete the original file from '~/Downloads'.
        - Emits log messages describing resolution steps.

    Notes:
        - Files are selected from Downloads based on the most recent modification time.
        - The function prefers local files over Downloads when available.
    """
    if selected_arg:
        p = Path(selected_arg).expanduser().resolve()
        if not p.exists():
            log.error("Selected file '%s' doesn't exist.", p)
            sys.exit(1)
        if not p.is_file():
            log.error("Selected path '%s' is not a file.", p)
            sys.exit(1)
        return p

    cwd = Path.cwd()

    local_candidates = [
        cwd / "selected.json",
        cwd / "astanalyzer-selected.json",
    ]
    for candidate in local_candidates:
        if candidate.exists() and candidate.is_file():
            log.info("Using selected JSON from working directory: %s", candidate)
            return candidate

    downloads = Path.home() / "Downloads"
    if not downloads.exists() or not downloads.is_dir():
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
        log.error(
            "No selected JSON found in working directory or Downloads "
            "(looked for 'selected.json', 'astanalyzer-selected.json', "
            "and '~/Downloads/astanalyzer-selected*.json')."
        )
        sys.exit(1)

    newest = candidates[0]

    if not copy_from_downloads:
        log.info("Using selected JSON directly from Downloads: %s", newest)
        return newest.resolve()

    target = cwd / newest.name

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


def check_patch_files(
    patch_files: list[Path],
    *,
    display_root: Path | None = None,
) -> tuple[int, int]:
    """
    Validate the given patch files using 'git apply --check'.

    Each patch is checked in the context of its parent directory.
    """
    if not patch_files:
        print("No patch files found.")
        return 0, 0

    ok = 0
    failed = 0
    root = display_root.resolve() if display_root is not None else None

    print_section("ASTANALYZER PATCH CHECK")
    if root is not None:
        print(f"Root: {root}")
    print(f"Patches found: {len(patch_files)}")

    for patch in sorted(patch_files):
        patch_dir = patch.parent

        if root is not None:
            try:
                shown_path = patch.relative_to(root)
            except ValueError:
                shown_path = patch
        else:
            shown_path = patch

        result = subprocess.run(
            ["git", "apply", "--check", patch.name],
            cwd=patch_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            ok += 1
            print(f"[OK]   {shown_path}")
        else:
            failed += 1
            print(f"[FAIL] {shown_path}")
            if result.stderr.strip():
                print(result.stderr.strip())

    return ok, failed


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


def check_all_patches(root: Path | None = None) -> tuple[int, int]:
    """
    Validate all patch files in the working directory using 'git apply --check'.

    This function discovers all '.patch' files under the current working directory
    (excluding the archive directory) and verifies whether they can be applied
    cleanly using Git. Each patch is checked in its own directory context.

    Args:
        None

    Returns:
        tuple[int, int]:
            - Number of patches that passed the check
            - Number of patches that failed

    Side Effects:
        - Executes external 'git apply --check' commands.
        - Prints a summary and per-patch results to stdout.
        - May output error messages from Git for failed patches.

    Notes:
        - Patch discovery excludes the archive directory by default.
        - Each patch is checked relative to its parent directory.
        - This operation does not modify any files.
    """
    root = (root or Path.cwd()).resolve()
    patch_files = find_patch_files(root, include_archive=False)

    if not patch_files:
        print("No patch files found.")
        return 0, 0

    ok = 0
    failed = 0

    print_section("ASTANALYZER PATCH CHECK")
    print(f"Root: {root}")
    print(f"Patches found: {len(patch_files)}")

    for patch in patch_files:
        rel_patch = patch.relative_to(root)
        patch_dir = patch.parent

        result = subprocess.run(
            ["git", "apply", "--check", patch.name],
            cwd=patch_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            ok += 1
            print(f"[OK]   {rel_patch}")
        else:
            failed += 1
            print(f"[FAIL] {rel_patch}")
            if result.stderr.strip():
                print(result.stderr.strip())

    return ok, failed


def apply_all_patches(root: Path | None = None) -> tuple[int, int]:
    """
    Apply all patch files in the working directory using 'git apply'.

    This function discovers all '.patch' files under the current working
    directory (excluding the archive directory) and attempts to apply each
    patch using Git. Each patch is applied in the context of its parent directory.

    Args:
        None

    Returns:
        tuple[int, int]:
            - Number of successfully applied patches
            - Number of failed patch applications

    Side Effects:
        - Modifies files in the working directory by applying patches.
        - Executes external 'git apply' commands.
        - Prints a summary and per-patch results to stdout.
        - May output error messages from Git for failed patches.

    Notes:
        - Patch discovery excludes the archive directory by default.
        - Each patch is applied relative to its parent directory.
        - It is recommended to run a check (e.g. 'git apply --check') before applying patches.
        - Partial application may occur if some patches succeed and others fail.
    
    Requires:
        Git must be installed and available in the system PATH.
    """
    root = (root or Path.cwd()).resolve()
    patch_files = find_patch_files(root, include_archive=False)

    if not patch_files:
        print("No patch files found.")
        return 0, 0

    ok = 0
    failed = 0

    print_section("ASTANALYZER APPLY SUMMARY")
    print(f"Root: {root}")
    print(f"Patches found: {len(patch_files)}")

    for patch in patch_files:
        rel_patch = patch.relative_to(root)
        patch_dir = patch.parent

        result = subprocess.run(
            ["git", "apply", patch.name],
            cwd=patch_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            ok += 1
            print(f"[OK]   {rel_patch}")
        else:
            failed += 1
            print(f"[FAIL] {rel_patch}")
            if result.stderr.strip():
                print(result.stderr.strip())

    return ok, failed


def cmd_scan(args: argparse.Namespace) -> None:
    """
    Run static analysis for the selected path and generate output reports.

    The command validates the input path, scans discovered Python files,
    saves the analysis results as JSON and HTML reports, and prints a summary.
    If enabled, it also opens the generated HTML report in a web browser.

    Rule selection and directory exclusion are resolved before scan execution.

    Args:
        args: Parsed CLI arguments containing the scan target and output options.

    Side Effects:
        - Writes 'scan_report.json' and 'report.html' to the current working directory.
        - May open the generated HTML report in a browser.
        - Prints summary information to stdout.
    """
    path = validate_path(args.path)

    files = get_list_of_files_in_project(str(path))

    excluded_dir_names = parse_excluded_dir_names(args.exclude_dir)
    if excluded_dir_names:
        files = [
            file_path
            for file_path in files
            if not any(part in excluded_dir_names for part in Path(file_path).parts)
        ]

    if not files:
        log.error("No files selected for scan after applying --exclude-dir.")
        sys.exit(2)

    project = load_project(files)

    selected_rules = getattr(args, "selected_rules", None)

    report, scan = run_rules_on_project_report(
        project,
        True,
        False,
        rules=selected_rules,
    )

    json_path = Path("scan_report.json").resolve()
    json_path.write_text(
        json.dumps(scan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info("Scan report JSON saved to: %s", json_path)

    html_path = Path("report.html").resolve()
    write_report_html(scan, html_path)
    log.info("Scan report HTML saved to: %s", html_path)

    if not args.no_open:
        open_report_in_browser(html_path)
        log.info("Report opened in browser.")

    print_section("ASTANALYZER SCAN SUMMARY")
    print(report.to_text())
    print()


def cmd_report(args: argparse.Namespace) -> None:
    """Open an existing HTML report in the default web browser."""
    report_path = validate_path(args.path)
    open_report_in_browser(report_path)
    log.info("Report opened in browser: %s", report_path)


def cmd_patch(args: argparse.Namespace) -> None:
    """
    Generate patch files from selected fixes and validate them.

    This command resolves the selected JSON input, parses its content,
    normalizes referenced file paths, and generates patch files based on
    selected findings. After generation, all patches are validated using
    'git apply --check'.

    Args:
        args: Parsed CLI arguments. Expected to contain:
            - selected: optional path to selected JSON file

    Returns:
        None

    Side Effects:
        - Reads and parses a JSON file containing selected findings.
        - May terminate the program if the JSON is invalid.
        - Modifies source files to ensure a trailing newline.
        - Generates '.patch' files in the working directory.
        - Executes 'git apply --check' to validate patches.
        - Prints a summary of generated and validated patches.

    Notes:
        - If no patches are generated, validation is skipped.
        - Patch validation excludes files stored in the archive directory.
    """
    selected_arg = args.selected_path or args.selected
    selected = resolve_selected_input(selected_arg)
    log.info("Using selected JSON: %s", selected)

    try:
        data = json.loads(selected.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        log.error("Invalid JSON in '%s': %s", selected, exc)
        sys.exit(1)

    project_root = normalize_project_root(data.get("project_root"))

    selected_files = collect_selected_files(
        data,
        base_dir=selected.parent,
        project_root=project_root,
    )
    for path in selected_files:
        ensure_final_newline(path)
        
    _, patch_count = build_patches_from_selected_json(
        data,
        base_dir=selected.parent,
        project_root=project_root,
    )

    if patch_count == 0:
        print("No patches were generated.")
        return

    check_root = project_root or selected.parent.resolve()
    ok, failed = check_all_patches(check_root)

    print_section("ASTANALYZER PATCH SUMMARY")
    print(f"Patches generated: {patch_count}")
    print(f"Patch checks OK:   {ok}")
    print(f"Patch checks FAIL: {failed}")
    print()


def cmd_apply(args: argparse.Namespace) -> None:
    """
    Validate, apply, and archive patch files from the current working directory.

    This command discovers all non-archived '.patch' files under the current
    working directory, validates them using 'git apply --check', and optionally
    applies them. If all patch applications succeed, related run artifacts and
    patch files are archived into a timestamped archive directory.

    Args:
        args: Parsed CLI arguments. Expected to contain:
            - check: if True, only validate patches and do not apply them

    Returns:
        None

    Side Effects:
        - Prints validation and application summaries to stdout.
        - Executes external Git commands for patch checking and application.
        - Modifies files in the working directory when patches are applied.
        - Creates a timestamped archive directory after a successful apply.
        - Moves generated artifacts and patch files into the archive directory.

    Notes:
        - Patch discovery excludes the archive directory.
        - Application is aborted if any patch fails the pre-check step.
        - In check-only mode, no patches are applied and no archive is created.
        - Archiving is skipped if any patch application fails.
    """
    patch_files = find_patch_files(Path.cwd(), include_archive=False)

    if not patch_files:
        print("No patch files found. Nothing to apply.")
        return

    ok, failed = check_all_patches()

    print_section("ASTANALYZER APPLY CHECK SUMMARY")
    print(f"Patches found:     {len(patch_files)}")
    print(f"Patch checks OK:   {ok}")
    print(f"Patch checks FAIL: {failed}")

    if failed > 0:
        print("Apply aborted because some patches failed check.")
        print()
        return

    if args.check:
        print("Check only mode enabled. No patches were applied.")
        print()
        return

    apply_ok, apply_failed = apply_all_patches()

    print_section("ASTANALYZER APPLY SUMMARY")
    print(f"Patch apply OK:    {apply_ok}")
    print(f"Patch apply FAIL:  {apply_failed}")

    if apply_failed > 0:
        print("Archive skipped because some patch applies failed.")
        print()
        return

    archive_dir = create_run_archive_dir(Path.cwd())

    archived_files = archive_run_artifacts(
        archive_dir=archive_dir,
        base_dir=Path.cwd(),
    )
    archived_patches = archive_patch_files_from_root(
        archive_dir=archive_dir,
        base_dir=Path.cwd(),
    )

    print_section("ASTANALYZER FINALIZE")
    print(f"Archive dir:       {archive_dir}")
    print(f"Archived files:    {len(archived_files)}")
    print(f"Archived patches:  {archived_patches}")
    print()


def cmd_archive(args: argparse.Namespace) -> None:
    """
    Archive generated analysis artifacts and patch files without applying them.

    This command stores the current working artifacts into a timestamped
    archive directory under 'used_patches'. Unlike the apply command, it does
    not validate or apply patches.

    Args:
        args: Parsed CLI arguments.

    Returns:
        None

    Side Effects:
        - Creates a timestamped archive directory when there is something to archive.
        - Moves generated JSON, HTML, and patch files into the archive directory.
        - Prints an archive summary to stdout.
    """
    root = Path.cwd()

    selected_path = None
    if getattr(args, "selected", None):
        selected_path = Path(args.selected).expanduser().resolve()
        if not selected_path.exists() or not selected_path.is_file():
            log.error("Selected JSON '%s' does not exist or is not a file.", selected_path)
            sys.exit(1)

    project_root = read_project_root_from_selected_json(selected_path)
    patch_root = project_root or root

    has_local_artifacts = has_working_artifacts(root)
    has_project_patches = bool(find_patch_files(patch_root, include_archive=False))

    if not has_local_artifacts and not has_project_patches:
        print("Nothing to archive.")
        return

    archive_dir = create_run_archive_dir(root)

    archived_files = archive_run_artifacts(
        archive_dir=archive_dir,
        base_dir=root,
    )
    archived_patches = archive_patch_files_from_root(
        archive_dir=archive_dir,
        base_dir=patch_root,
    )

    print_section("ASTANALYZER ARCHIVE SUMMARY")
    print(f"Archive dir:       {archive_dir}")
    print(f"Archived files:    {len(archived_files)}")
    print(f"Archived patches:  {archived_patches}")
    print()


def cmd_clean(args: argparse.Namespace) -> None:
    """
    Clean generated artifacts and patch files from the working directory.

    This command removes known analysis outputs and all '.patch' files.
    Optionally, it can also delete the archive directory containing
    previously stored patches. When archive deletion is requested, the
    user is prompted for confirmation.

    Args:
        args: Parsed CLI arguments. Expected to contain:
            - include_archive: whether to delete the archive directory
            - verbose_list: whether to print all removed paths

    Returns:
        None

    Side Effects:
        - Permanently deletes files from the working directory.
        - May recursively delete the archive directory.
        - Prompts the user for confirmation before deleting the archive.
        - Prints a summary of removed items to stdout.

    Notes:
        - Patch files stored in the archive directory are preserved unless
          explicitly removed via `--include-archive`.
        - The operation is irreversible.
    """
    if args.include_archive:
        confirm = input("Delete archive too? [y/N]: ")
        if confirm.lower() != "y":
            print("Aborted.")
            return

    removed_count, removed_paths = clean_working_artifacts(
        include_archive=args.include_archive,
        base_dir=Path.cwd(),
    )

    print_section("ASTANALYZER CLEAN SUMMARY")
    print(f"Removed items: {removed_count}")

    if removed_count == 0:
        print("Nothing to clean.")

    if args.verbose_list:
        print("\nRemoved items:")
        for p in removed_paths:
            print(f" - {p}")
    print()


def add_rules_argument(parser: argparse.ArgumentParser) -> None:
    """
    Add a CLI argument for specifying custom rule files or directories.

    This function extends the given argument parser with a '--rules' option,
    allowing users to provide one or more paths to custom rule definitions.
    The argument can be used multiple times to include multiple sources.

    Args:
        parser (argparse.ArgumentParser): The argument parser to extend.

    Returns:
        None

    Side Effects:
        - Modifies the provided argument parser by adding a new argument.

    Notes:
        - The '--rules' argument accepts both file and directory paths.
        - When used multiple times, all provided paths are collected into a list.
    """
    parser.add_argument(
        "--rules",
        action="append",
        default=[],
        help="Path to a custom rule file or directory. Can be used multiple times.",
    )


def add_scan_filter_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add CLI arguments for rule and directory filtering during scan.

    Args:
        parser (argparse.ArgumentParser): Parser for the scan command.
    """
    parser.add_argument(
        "--only",
        help="Comma-separated list of rule IDs to include, e.g. STYLE-002,STYLE-003",
    )
    parser.add_argument(
        "--exclude",
        help="Comma-separated list of rule IDs to exclude, e.g. SEC-031,DBG-023",
    )
    parser.add_argument(
        "--only-category",
        help="Comma-separated list of rule categories to include, e.g. STYLE,SECURITY",
    )
    parser.add_argument(
        "--exclude-category",
        help="Comma-separated list of rule categories to exclude, e.g. STYLE,DEBUG",
    )
    parser.add_argument(
        "--exclude-dir",
        help="Comma-separated directory names to skip during scan, e.g. tests,venv,migrations",
    )
    parser.add_argument(
        "--include",
        help="Comma-separated list of rule IDs to include even if excluded by filters",
    )


def build_parser() -> argparse.ArgumentParser:
    """
    Build the CLI parser with all commands and options for astanalyzer.

    The parser defines global options (verbosity, quiet mode) and registers
    subcommands such as 'scan', 'patch', 'apply', 'clean', and 'report',
    each mapped to its corresponding handler function.

    Returns:
        argparse.ArgumentParser: Fully configured CLI parser.
    """
    parser = argparse.ArgumentParser(
        description="astanalyzer static analysis tool"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v, -vv)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Show only errors",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    report_parser = subparsers.add_parser("report", help="Open existing HTML report")
    report_parser.add_argument(
        "path",
        nargs="?",
        default="report.html",
        help="Path to HTML report",
    )
    report_parser.set_defaults(func=cmd_report)

    clean_parser = subparsers.add_parser("clean", help="Delete working artefacts and patches")
    clean_parser.add_argument(
        "--include-archive",
        action="store_true",
        help="Delete the used_patches archive too",
    )
    clean_parser.add_argument(
        "--verbose-list",
        action="store_true",
        help="Print all removed files",
    )
    clean_parser.set_defaults(func=cmd_clean)

    scan_parser = subparsers.add_parser("scan", help="Run project scan")
    scan_parser.add_argument(
        "path",
        help="Path to a Python file or directory",
    )
    scan_parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open HTML report automatically after scan",
    )
    add_rules_argument(scan_parser)
    add_scan_filter_arguments(scan_parser)
    scan_parser.set_defaults(func=cmd_scan)

    patch_parser = subparsers.add_parser("patch", help="Generate patches from selected fixes")
    patch_parser.add_argument(
        "selected",
        nargs="?",
        default=None,
        help="Selected fixes JSON file; if missing, uses local file or newest from Downloads",
    )
    patch_parser.add_argument(
        "--selected",
        dest="selected_path",
        help="Explicit path to selected JSON file",
    ) 
    patch_parser.set_defaults(func=cmd_patch)

    apply_parser = subparsers.add_parser("apply", help="Apply existing .patch files")
    apply_parser.add_argument(
        "--check",
        action="store_true",
        help="Only verify patch files, do not apply them",
    )
    apply_parser.set_defaults(func=cmd_apply)

    archive_parser = subparsers.add_parser(
        "archive",
        help="Archive generated artefacts and patches without applying them",
    )
    archive_parser.add_argument(
        "selected",
        nargs="?",
        default=None,
        help="Selected fixes JSON file used to resolve project_root for patch archiving",
    )
    archive_parser.set_defaults(func=cmd_archive)

    return parser


def main(argv: list[str] | None = None) -> int:
    """
    Run the astanalyzer CLI application.

    Parses arguments, sets up logging, loads rules, resolves scan-time rule
    selection, and executes the selected command.

    Args:
        argv (list[str] | None): Optional CLI arguments.

    Returns:
        int: Exit status code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.quiet:
        log_level = "ERROR"
    elif args.verbose == 0:
        log_level = "WARNING"
    elif args.verbose == 1:
        log_level = "INFO"
    else:
        log_level = "DEBUG"

    setup_logging(log_level)

    load_builtin_rules()

    for rules_path in getattr(args, "rules", []):
        imported = import_rules_from_path(rules_path)
        log.info("Imported %d custom rule file(s) from %s", len(imported), rules_path)

    all_rules = list(Rule.registry)

    if args.command == "scan":
        selection = build_rule_selection(
            only=args.only,
            exclude=args.exclude,
            only_category=args.only_category,
            exclude_category=args.exclude_category,
            include=args.include,
        )

        try:
            selected_rules = filter_rules(all_rules, selection)
        except RuleFilterError as exc:
            log.error("Rule selection error: %s", exc)
            sys.exit(2)

        args.selected_rules = selected_rules

        log.info(
            "Selected %d rule(s) for scan out of %d loaded rule(s).",
            len(selected_rules),
            len(all_rules),
        )
    else:
        args.selected_rules = None

    log.info("astanalyzer started")
    args.func(args)
    return 0
