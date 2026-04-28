"""Parser construction and entry point for the astanalyzer CLI."""

from __future__ import annotations

import argparse
import logging
import sys

from ..logging_config import setup_logging
from ..rule import Rule
from ..rule_filtering import RuleFilterError, build_rule_selection, filter_rules
from ..rule_loader import import_rules_from_path
from ..rules import load_builtin_rules
from .commands.apply import cmd_apply
from .commands.archive import cmd_archive
from .commands.clean import cmd_clean
from .commands.patch import cmd_patch
from .commands.report import cmd_report
from .commands.scan import cmd_scan

log = logging.getLogger(__name__)

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
        "output",
        nargs="?",
        default=None,
        choices=["archive"],
        help="Optional scan output mode",
    )
    scan_parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open HTML report automatically after scan",
    )
    scan_parser.add_argument(
    "--policy",
    choices=["default", "ci", "strict"],
    default="default",
    help="Severity policy profile to apply during scan",
    )
    add_rules_argument(scan_parser)
    add_scan_filter_arguments(scan_parser)
    scan_parser.set_defaults(func=cmd_scan)

    patch_parser = subparsers.add_parser("patch", help="Generate patches from selected fixes")
    patch_parser.add_argument(
        "selected_json_path",
        nargs="?",
        default=None,
        metavar="selected_json_path",
        help="Selected fixes JSON file; if omitted, uses cwd fallback or newest file from Downloads",
    )
    patch_parser.add_argument(
        "--selected",
        dest="deprecated_selected",
        help="Deprecated alias for selected_json_path",
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
        "selected_json_path",
        nargs="?",
        default=None,
        metavar="selected_json_path",
        help="Selected fixes JSON file used to resolve project_root for patch archiving",
    )
    archive_parser.add_argument(
        "--selected",
        dest="deprecated_selected",
        help="Deprecated alias for selected_json_path",
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
