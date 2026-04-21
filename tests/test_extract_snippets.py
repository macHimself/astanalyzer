from pathlib import Path

import pytest

# Uprav podle skutečné cesty v projektu
from astanalyzer.report_ui import build_report_html, highlight_python_code
from astanalyzer.engine.scan_runtime import extract_code_snippet


def test_extract_code_snippet_returns_context_range(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        "\n".join(
            [
                "line1",
                "line2",
                "line3",
                "line4",
                "line5",
                "line6",
                "line7",
                "line8",
                "line9",
                "line10",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end = extract_code_snippet(
        file_path=file_path,
        start_line=5,
        end_line=6,
        context=2,
    )

    assert snippet is not None
    assert snippet_start == 3
    assert snippet_end == 8
    assert snippet.startswith("# ... truncated ...\n")
    assert "line3\nline4\nline5\nline6\nline7\nline8\n" in snippet


def test_extract_code_snippet_does_not_start_inside_triple_quoted_string(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "sample_docstring.py"
    file_path.write_text(
        "\n".join(
            [
                "def example():",
                '    """',
                "    first line of docstring",
                "    second line of docstring",
                '    """',
                "    if value:",
                "        return 1",
                "    return 0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end = extract_code_snippet(
        file_path=file_path,
        start_line=6,
        end_line=7,
        context=2,
    )

    assert snippet is not None
    assert snippet_start is not None
    assert snippet_end is not None

    # Snippet nesmí začít uprostřed docstringu.
    assert snippet_start <= 2
    assert '"""' in snippet
    assert "if value:" in snippet
    assert "return 1" in snippet


def test_highlight_python_code_marks_requested_lines() -> None:
    code = (
        "def f():\n"
        "    value = 1\n"
        "    if value:\n"
        "        return value\n"
    )

    html = highlight_python_code(
        code,
        snippet_start_line=10,
        match_start_line=12,
        match_end_line=13,
    )

    assert "codehilite" in html
    assert "def" in html
    assert "return" in html
    assert "12" in html or "13" in html


def test_highlight_python_code_marks_requested_lines_hll() -> None:
    code = (
        "def f():\n"
        "    value = 1\n"
        "    if value:\n"
        "        return value\n"
    )

    html = highlight_python_code(
        code,
        snippet_start_line=10,
        match_start_line=12,
        match_end_line=13,
    )

    assert "codehilite" in html
    assert "hll" in html


def test_build_report_html_contains_collapsible_rule_description_and_code_context() -> None:
    report_data = {
        "project_root": "/tmp/project",
        "findings": [
            {
                "id": "F-001",
                "rule_id": "STYLE-001",
                "title": "Empty block",
                "severity": "warning",
                "file": "sample.py",
                "start_line": 10,
                "end_line": 11,
                "snippet_start_line": 8,
                "snippet_end_line": 14,
                "message": "This block contains no executable logic.",
                "code_snippet": (
                    "x = 1\n"
                    "if something:\n"
                    "    pass\n"
                    "return x\n"
                ),
                "anchor": {
                    "anchor_id": "abc",
                    "file": "sample.py",
                    "rule_id": "STYLE-001",
                    "node_type": "If",
                    "symbol_path": None,
                    "line": 10,
                    "col": 0,
                    "end_line": 11,
                    "end_col": 8,
                    "source_hash": "src",
                    "context_hash": "ctx",
                },
                "fixes": [
                    {
                        "fix_id": "FX-001-A",
                        "title": "Proposed fix",
                        "reason": "Empty block should contain real logic or be removed.",
                        "dsl": {
                            "because": "Empty block should contain real logic or be removed.",
                            "actions": [
                                {
                                    "op": "insert_at_body_start",
                                    "text": "# TODO: implement block logic",
                                }
                            ],
                        },
                        "fixer_index": 0,
                    }
                ],
            }
        ],
    }

    html = build_report_html(report_data)

    assert "Rule description" in html
    assert "View code context" in html
    assert "Show details" in html
    assert "codehilite" in html
    assert "Empty block" in html
    assert "This block contains no executable logic." in html