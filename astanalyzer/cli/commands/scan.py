"""Implementation of the astanalyzer scan command."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from ...engine import get_list_of_files_in_project, load_project, run_rules_on_project_report
from ...file_selection import parse_excluded_dir_names
from ...report_ui import open_report_in_browser, write_report_html
from ..utils.files import validate_path
from ..utils.output import print_section

log = logging.getLogger(__name__)

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
