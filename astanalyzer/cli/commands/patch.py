"""Implementation of the astanalyzer patch command."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from ...engine import build_patches_from_selected_json, normalize_project_root
from ..utils.files import collect_selected_files, ensure_final_newline
from ..utils.output import print_section
from ..utils.patches import check_all_patches
from ..utils.selected import resolve_selected_cli_argument, resolve_selected_input

log = logging.getLogger(__name__)

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
    selected_arg = resolve_selected_cli_argument(
        getattr(args, "selected_json_path", None),
        getattr(args, "deprecated_selected", None),
    )
    selected = resolve_selected_input(selected_arg)
    if selected is None:
        log.error("Selected JSON could not be resolved.")
        sys.exit(1)
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
