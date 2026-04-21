from __future__ import annotations

import json
from pathlib import Path

from astanalyzer.cli import collect_selected_files
from astanalyzer.engine import build_patches_from_selected_json, load_project, run_rules_on_project_report


SOURCE_CODE = "def x():\n    return 1\n    return 2\n"


def _scan_project(project_root: Path, source: Path):
    project = load_project([str(source)])
    project.root_dir = project_root
    _, scan = run_rules_on_project_report(project, build_plans=True, build_fixes=False)
    assert scan["findings"]
    assert scan["project_root"] == str(project_root.resolve())
    return scan


def _first_selected(scan: dict) -> dict:
    return {"project_root": scan["project_root"], "findings": [scan["findings"][0]]}


def test_patch_generation_with_json_in_project_root(tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    source = project_root / "a.py"
    source.write_text(SOURCE_CODE, encoding="utf-8")

    scan = _scan_project(project_root, source)
    selected = _first_selected(scan)

    patch_dir, count = build_patches_from_selected_json(
        selected,
        base_dir=project_root,
    )

    assert patch_dir is not None
    assert count >= 1
    assert list(project_root.glob("a.py__*.patch"))


def test_patch_generation_with_json_outside_project_root(tmp_path: Path):
    project_root = tmp_path / "project"
    export_dir = tmp_path / "exports"
    project_root.mkdir()
    export_dir.mkdir()

    source = project_root / "pkg" / "a.py"
    source.parent.mkdir()
    source.write_text(SOURCE_CODE, encoding="utf-8")

    scan = _scan_project(project_root, source)
    selected = _first_selected(scan)

    selected_path = export_dir / "astanalyzer-selected.json"
    selected_path.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")

    resolved_files = collect_selected_files(selected, base_dir=selected_path.parent)
    assert resolved_files == [source.resolve()]

    patch_dir, count = build_patches_from_selected_json(
        selected,
        base_dir=selected_path.parent,
    )

    assert patch_dir is not None
    assert count >= 1
    assert list(source.parent.glob("a.py__*.patch"))


def test_patch_generation_from_different_cwd(tmp_path: Path, monkeypatch):
    project_root = tmp_path / "project"
    foreign_cwd = tmp_path / "elsewhere"
    project_root.mkdir()
    foreign_cwd.mkdir()

    source = project_root / "a.py"
    source.write_text(SOURCE_CODE, encoding="utf-8")

    scan = _scan_project(project_root, source)
    selected = _first_selected(scan)

    monkeypatch.chdir(foreign_cwd)

    patch_dir, count = build_patches_from_selected_json(
        selected,
        base_dir=foreign_cwd,
    )

    assert patch_dir is not None
    assert count >= 1
    assert list(project_root.glob("a.py__*.patch"))
    assert not list(foreign_cwd.glob("a.py__*.patch"))


def test_patch_generation_accepts_relative_and_absolute_finding_paths(tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()

    source = project_root / "nested" / "a.py"
    source.parent.mkdir()
    source.write_text(SOURCE_CODE, encoding="utf-8")

    scan = _scan_project(project_root, source)
    relative_selected = _first_selected(scan)

    absolute_selected = _first_selected(scan)
    absolute_selected["findings"][0] = dict(absolute_selected["findings"][0])
    absolute_selected["findings"][0]["file"] = str(source.resolve())

    relative_files = collect_selected_files(relative_selected, base_dir=tmp_path / "exports")
    absolute_files = collect_selected_files(absolute_selected, base_dir=tmp_path / "exports")

    assert relative_files == [source.resolve()]
    assert absolute_files == [source.resolve()]

    patch_dir_rel, count_rel = build_patches_from_selected_json(relative_selected, base_dir=tmp_path)
    patch_dir_abs, count_abs = build_patches_from_selected_json(absolute_selected, base_dir=tmp_path)

    assert patch_dir_rel is not None
    assert patch_dir_abs is not None
    assert count_rel >= 1
    assert count_abs >= 1


def test_collect_selected_files_uses_anchor_file_for_selected_action(tmp_path: Path):
    project_root = tmp_path / "project"
    export_dir = tmp_path / "exports"
    project_root.mkdir()
    export_dir.mkdir()

    source = project_root / "pkg" / "a.py"
    source.parent.mkdir()
    source.write_text("def x():\n    return 1\n", encoding="utf-8")

    selected_data = {
        "project_root": str(project_root.resolve()),
        "findings": [],
        "selected_actions": [
            {
                "type": "ignore_finding",
                "rule_id": "STYLE-003",
                "anchor": {
                    "file": "pkg/a.py",
                    "start_line": 1,
                    "end_line": 2,
                },
            }
        ],
    }

    files = collect_selected_files(selected_data, base_dir=export_dir)
    assert files == [source.resolve()]


def test_collect_selected_files_accepts_absolute_anchor_file(tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()

    source = project_root / "a.py"
    source.write_text("def x():\n    return 1\n", encoding="utf-8")

    selected_data = {
        "project_root": str(project_root.resolve()),
        "findings": [],
        "selected_actions": [
            {
                "type": "ignore_finding",
                "rule_id": "STYLE-003",
                "anchor": {
                    "file": str(source.resolve()),
                    "start_line": 1,
                    "end_line": 2,
                },
            }
        ],
    }

    files = collect_selected_files(selected_data, base_dir=tmp_path / "exports")
    assert files == [source.resolve()]


def test_patch_generation_uses_anchor_file_from_selected_action(tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()

    source = project_root / "a.py"
    source.write_text("def x():\n    return 1\n    return 2\n", encoding="utf-8")

    project = load_project([str(source)])
    project.root_dir = project_root
    _, scan = run_rules_on_project_report(project, build_plans=True, build_fixes=False)
    assert scan["findings"]

    finding = next(
        dict(f)
        for f in scan["findings"]
        if (f.get("anchor") or {}).get("node_type") == "FunctionDef"
    )

    selected_data = {
        "project_root": scan["project_root"],
        "findings": [],
        "selected_actions": [
            {
                "type": "ignore_finding",
                "finding_id": finding["id"],
                "rule_id": finding["rule_id"],
                "anchor": dict(finding["anchor"]),
            }
        ],
    }

    patch_dir, count = build_patches_from_selected_json(
        selected_data,
        base_dir=tmp_path,
        project_root=project_root,
    )

    assert patch_dir is not None
    assert count >= 1
