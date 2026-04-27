"""
HTML report UI generation for astanalyzer.
"""

from __future__ import annotations

import json
import webbrowser
from pathlib import Path

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer

from .favicon import ensure_report_favicon
from .script_loader import build_report_script
from .styles import build_report_styles
from .templates import build_report_shell


def highlight_python_code(
    code: str,
    snippet_start_line: int | None = None,
    match_start_line: int | None = None,
    match_end_line: int | None = None,
) -> str:
    """Return syntax-highlighted HTML for a Python code snippet."""
    if not code:
        return ""

    lines = code.splitlines()

    leading_blank_count = 0
    for line in lines:
        if line.strip() == "":
            leading_blank_count += 1
        else:
            break

    if leading_blank_count:
        lines = lines[leading_blank_count:]
        code = "\n".join(lines)

    adjusted_snippet_start = (snippet_start_line or 1) + leading_blank_count

    hl_lines: list[int] = []
    if match_start_line is not None and match_end_line is not None:
        start_rel = max(1, match_start_line - adjusted_snippet_start + 1)
        end_rel = max(start_rel, match_end_line - adjusted_snippet_start + 1)
        hl_lines = list(range(start_rel, end_rel + 1))

    formatter = HtmlFormatter(
        nowrap=False,
        cssclass="codehilite",
        linenos="table",
        linenostart=adjusted_snippet_start,
        hl_lines=hl_lines,
    )

    return highlight(code, PythonLexer(), formatter)


def prepare_report_data(report_data: dict) -> dict:
    """Prepare report data for embedding into the HTML report."""
    prepared = json.loads(json.dumps(report_data))

    for finding in prepared.get("findings", []):
        snippet = finding.get("code_snippet", "") or ""

        finding["code_snippet_html"] = (
            highlight_python_code(
                snippet,
                snippet_start_line=finding.get("snippet_start_line"),
                match_start_line=finding.get("start_line"),
                match_end_line=finding.get("end_line"),
            )
            if snippet
            else ""
        )

    return prepared


def build_report_html(report_data: dict) -> str:
    """Build a standalone HTML report page from scan JSON data."""
    prepared_data = prepare_report_data(report_data)

    safe_json = (
        json.dumps(prepared_data, ensure_ascii=False, indent=2)
        .replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )

    pygments_css = HtmlFormatter(cssclass="codehilite").get_style_defs(".codehilite")

    styles = build_report_styles(pygments_css)
    script = build_report_script(safe_json)

    return build_report_shell(styles=styles, script=script)


def write_report_html(scan_data: dict, output_path: Path) -> Path:
    """Write standalone HTML report to disk and return the output path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ensure_report_favicon(output_path.parent)

    html = build_report_html(scan_data)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def open_report_in_browser(report_path: Path) -> None:
    """Open generated HTML report in the default browser."""
    webbrowser.open(report_path.resolve().as_uri(), new=2)
