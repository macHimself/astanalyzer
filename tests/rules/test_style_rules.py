import pytest
from astanalyzer.engine import load_project, run_rules_on_project_report


def test_missing_docstring_detected(tmp_path):
    source = tmp_path / "a.py"
    source.write_text(
        "def foo():\n"
        "    return 1\n",
        encoding="utf-8",
    )

    project = load_project([str(source)])
    project.root_dir = tmp_path

    _, scan = run_rules_on_project_report(
        project,
        build_plans=True,
        build_fixes=False,
    )

    rule_ids = [f["rule_id"] for f in scan["findings"]]

    assert "STYLE-002" in rule_ids


def test_missing_docstring_not_detected_when_present(tmp_path):
    source = tmp_path / "a.py"
    source.write_text(
        'def foo():\n'
        '    """This is a docstring."""\n'
        '    return 1\n',
        encoding="utf-8",
    )

    project = load_project([str(source)])
    project.root_dir = tmp_path

    _, scan = run_rules_on_project_report(
        project,
        build_plans=True,
        build_fixes=False,
    )

    rule_ids = [f["rule_id"] for f in scan["findings"]]

    assert "STYLE-002" not in rule_ids