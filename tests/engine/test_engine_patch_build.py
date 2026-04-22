from pathlib import Path

from astanalyzer.engine import (
    build_patches_from_selected_json,
    load_project,
    run_rules_on_project_report,
)


def test_patch_generation_from_selected(tmp_path, make_project):
    project = make_project({
        "a.py": "def x():\n    return 1\n    return 2\n"
    })

    report, scan = run_rules_on_project_report(project, True, True)

    assert scan["findings"]

    selected = {
        "findings": [scan["findings"][0]]
    }

    patch_dir, count = build_patches_from_selected_json(
        selected,
        base_dir=tmp_path,
    )

    assert count >= 1


def test_patch_generation_from_selected(tmp_path):
    source = tmp_path / "a.py"
    source.write_text(
        "def x():\n    return 1\n    return 2\n",
        encoding="utf-8",
    )

    project = load_project([str(source)])
    project.root_dir = tmp_path

    report, scan = run_rules_on_project_report(project, build_plans=True, build_fixes=False)

    assert scan["findings"]

    selected = {
        "findings": [scan["findings"][0]],
    }

    patch_dir, count = build_patches_from_selected_json(
        selected,
        base_dir=tmp_path,
    )

    assert count >= 1
