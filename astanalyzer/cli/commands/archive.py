"""Implementation of the astanalyzer archive command."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..utils.archive import archive_patch_files_from_root, archive_run_artifacts, create_run_archive_dir, find_patch_files, has_working_artifacts
from ..utils.output import print_section
from ..utils.selected import read_project_root_from_selected_json, resolve_selected_cli_argument, resolve_selected_input

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

    selected_arg = resolve_selected_cli_argument(
        getattr(args, "selected_json_path", None),
        getattr(args, "deprecated_selected", None),
    )

    selected_path = resolve_selected_input(
        selected_arg,
        copy_from_downloads=True,
        required=False,
    )

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
