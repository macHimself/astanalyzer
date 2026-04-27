"""Command-line interface package for astanalyzer."""

from .main import build_parser, main

from .commands.archive import cmd_archive
from .commands.apply import cmd_apply
from .commands.clean import cmd_clean
from .commands.patch import (
    cmd_patch,
    collect_selected_files,
    ensure_final_newline,
)
from .commands.report import cmd_report
from .commands.scan import cmd_scan

from .utils.archive import (
    ARCHIVE_DIR_NAME,
    GENERATED_ARTIFACT_FILENAMES,
    archive_patch_files_from_root,
    archive_run_artifacts,
    clean_working_artifacts,
    create_run_archive_dir,
    ensure_archive_root,
    get_archive_root_path,
    has_working_artifacts,
    move_file_if_exists,
)

from .utils.patches import (
    apply_all_patches,
    check_all_patches,
    check_patch_files,
    find_patch_files,
)

from .utils.selected import (
    resolve_selected_cli_argument,
    resolve_selected_input,
)

from .utils.output import print_kv, print_section

__all__ = [
    "build_parser",
    "main",
    "cmd_archive",
    "cmd_apply",
    "cmd_clean",
    "cmd_patch",
    "cmd_report",
    "cmd_scan",
    "ARCHIVE_DIR_NAME",
    "GENERATED_ARTIFACT_FILENAMES",
    "archive_patch_files_from_root",
    "archive_run_artifacts",
    "clean_working_artifacts",
    "create_run_archive_dir",
    "ensure_archive_root",
    "get_archive_root_path",
    "has_working_artifacts",
    "move_file_if_exists",
    "apply_all_patches",
    "check_all_patches",
    "check_patch_files",
    "find_patch_files",
    "collect_selected_files",
    "ensure_final_newline",
    "resolve_selected_cli_argument",
    "resolve_selected_input",
    "print_kv",
    "print_section",
]
