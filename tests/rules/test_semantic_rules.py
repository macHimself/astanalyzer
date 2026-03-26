from astanalyzer.engine import run_rules_on_project_report
from astanalyzer.engine import load_project


def test_compare_to_none_using_eq_matches(tmp_path):
    source = tmp_path / "a.py"
    source.write_text(
        "def f(x):\n"
        "    if x == None:\n"
        "        return True\n",
        encoding="utf-8",
    )

    project = load_project([str(source)])
    project.root_dir = tmp_path

    report, scan = run_rules_on_project_report(
        project,
        build_plans=True,
        build_fixes=False,
    )

    rule_ids = [f["rule_id"] for f in scan["findings"]]

    assert "CMP-001" in rule_ids

def test_compare_to_none_using_is_does_not_match(tmp_path):
    source = tmp_path / "a.py"
    source.write_text(
        "def f(x):\n"
        "    if x is None:\n"
        "        return True\n",
        encoding="utf-8",
    )

    project = load_project([str(source)])
    project.root_dir = tmp_path

    report, scan = run_rules_on_project_report(
        project,
        build_plans=True,
        build_fixes=False,
    )

    rule_ids = [f["rule_id"] for f in scan["findings"]]

    assert "CMP-001" not in rule_ids