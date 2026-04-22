from astanalyzer.engine import run_rules_on_project_report


def test_engine_runs_scan_on_simple_project(make_project):
    project = make_project({
        "a.py": "def BadName():\n    return 1\n"
    })

    report, scan = run_rules_on_project_report(project, build_plans=True, build_fixes=False)

    assert report.files_analyzed == 1
    assert isinstance(scan, dict)
    assert "findings" in scan


def test_scan_detects_multiple_rules(make_project):
    project = make_project({
        "a.py": """
def BadName():
    if True:
        return 1
"""
    })

    report, scan = run_rules_on_project_report(project, True, False)

    rule_ids = {f["rule_id"] for f in scan["findings"]}

    assert "STYLE-005" in rule_ids
    assert "SEM-001" in rule_ids
