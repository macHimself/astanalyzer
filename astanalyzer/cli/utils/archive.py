"""Archive and cleanup helpers for generated astanalyzer artifacts."""

from __future__ import annotations

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

from ...report_ui import FAVICON_FILENAME

log = logging.getLogger(__name__)

ARCHIVE_DIR_NAME = "used_patches"

GENERATED_ARTIFACT_FILENAMES = [
    "astanalyzer-selected.json",
    "selected.json",
    "scan_report.json",
    "report.html",
    FAVICON_FILENAME,
]

def now_stamp() -> str:
    """Return current UTC timestamp formatted as 'YYYY-MM-DD_HH-MM-SS'."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")


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
        - astanalyzer.ico
    """
    root = base_dir or Path.cwd()
    archived: list[Path] = []

    candidates = [root / name for name in GENERATED_ARTIFACT_FILENAMES]

    for p in candidates:
        out = move_file_if_exists(p, archive_dir)
        if out is not None:
            archived.append(out)

    return archived


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

    candidates = [root / name for name in GENERATED_ARTIFACT_FILENAMES]

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
            * astanalyzer.ico
        - All '.patch' files under the root directory are removed.
        - Patch files inside the archive directory are skipped unless
          `include_archive=True`.
    """
    root = base_dir or Path.cwd()
    removed = 0
    removed_paths: list[Path] = []

    log.debug("Starting clean in: %s", root)

    archive_root = get_archive_root_path(root)

    normal_files = [root / name for name in GENERATED_ARTIFACT_FILENAMES]

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
