"""Implementation of the astanalyzer report command."""

from __future__ import annotations

import argparse
import logging

from ...report_ui import open_report_in_browser
from ..utils.files import validate_path

log = logging.getLogger(__name__)

def cmd_report(args: argparse.Namespace) -> None:
    """Open an existing HTML report in the default web browser."""
    report_path = validate_path(args.path)
    open_report_in_browser(report_path)
    log.info("Report opened in browser: %s", report_path)
