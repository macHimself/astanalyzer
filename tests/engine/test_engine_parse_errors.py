from pathlib import Path

from astanalyzer.engine import load_project

def test_load_project_collects_parse_errors(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text("def x(:\n    pass\n", encoding="utf-8")

    project = load_project([str(bad)])

    assert len(project.parse_errors) == 1
    assert project.parse_errors[0].file.endswith("bad.py")


