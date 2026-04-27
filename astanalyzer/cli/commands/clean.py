"""Implementation of the astanalyzer clean command."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..utils.archive import clean_working_artifacts
from ..utils.output import print_section

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
