"""Implementation of the astanalyzer apply command."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..utils.archive import archive_patch_files_from_root, archive_run_artifacts, create_run_archive_dir, find_patch_files
from ..utils.output import print_section
from ..utils.patches import apply_all_patches, check_all_patches

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
