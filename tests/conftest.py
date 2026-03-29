from __future__ import annotations

from pathlib import Path

import pytest
from astroid import parse

from astanalyzer.engine.project_loader import (
    ModuleNode,
    ProjectNode,
    attach_tree_metadata,
    load_project,
)

from astanalyzer.engine.scan_runtime import run_rules_on_project_report

import astanalyzer.rules


@pytest.fixture
def parse_code():
    def _parse(code: str, filename: str = "test_sample.py"):
        tree = parse(code, module_name=filename)
        attach_tree_metadata(tree, filename, code)
        return tree
    return _parse


@pytest.fixture
def make_project(parse_code):
    def _make_project(files: dict[str, str]) -> ProjectNode:
        project = ProjectNode()
        project.root_dir = Path.cwd()

        for filename, code in files.items():
            tree = parse_code(code, filename)
            project.add_module(ModuleNode(filename=filename, ast_root=tree))

        return project
    return _make_project


@pytest.fixture
def write_source(tmp_path):
    def _write_source(code: str, filename: str = "a.py") -> Path:
        source = tmp_path / filename
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(code, encoding="utf-8")
        return source
    return _write_source


@pytest.fixture
def load_project_from_code(write_source):
    def _load_project_from_code(code: str, filename: str = "a.py"):
        source = write_source(code, filename)
        project = load_project([str(source)])
        project.root_dir = source.parent
        return project
    return _load_project_from_code


@pytest.fixture
def run_scan(load_project_from_code):
    from astanalyzer.rule import Rule

    print("RULE COUNT:", len(Rule.registry))
    print("RULE IDS:", [getattr(r, "id", type(r).__name__) for r in Rule.registry])
    def _run_scan(code: str, filename: str = "a.py", *, build_plans: bool = True, build_fixes: bool = False):
        project = load_project_from_code(code, filename)
        return run_rules_on_project_report(
            project,
            build_plans=build_plans,
            build_fixes=build_fixes,
        )
    return _run_scan


@pytest.fixture
def scan_rule_ids(run_scan):
    def _scan_rule_ids(code: str, filename: str = "a.py") -> list[str]:
        _, scan = run_scan(code, filename)
        return [f["rule_id"] for f in scan["findings"]]
    return _scan_rule_ids


@pytest.fixture
def scan_findings(run_scan):
    def _scan_findings(code: str, filename: str = "a.py"):
        _, scan = run_scan(code, filename)
        return scan["findings"]
    return _scan_findings