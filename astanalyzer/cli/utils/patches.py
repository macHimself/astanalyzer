"""Patch discovery, validation, and application helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .archive import find_patch_files
from .output import print_section

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
