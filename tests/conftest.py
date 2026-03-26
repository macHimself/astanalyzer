from __future__ import annotations

from pathlib import Path

import pytest
from astroid import parse

from astanalyzer.engine import attach_tree_metadata, ModuleNode, ProjectNode


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