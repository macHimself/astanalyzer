from __future__ import annotations

import pytest

from astanalyzer.engine import (
    get_list_of_files_in_project,
    load_project,
    resolve_project_root,
)


def test_load_project_loads_single_python_file(tmp_path):
    source = tmp_path / "a.py"
    source.write_text("x = 1\n", encoding="utf-8")

    project = load_project([str(source)])

    assert len(project.modules) == 1
    module = project.modules[0]
    assert module.filename == str(source)
    assert module.ast_root.file == str(source)
    assert module.ast_root.file_content == "x = 1\n"
    assert module.ast_root.file_by_lines == ["x = 1\n"]


def test_load_project_loads_multiple_files(tmp_path):
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("x = 1\n", encoding="utf-8")
    b.write_text("y = 2\n", encoding="utf-8")

    project = load_project([str(a), str(b)])

    assert len(project.modules) == 2
    names = {m.filename for m in project.modules}
    assert str(a) in names
    assert str(b) in names


def test_load_project_collects_syntax_error_without_crash(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text("def x(:\n    pass\n", encoding="utf-8")

    project = load_project([str(bad)])

    assert len(project.modules) == 0
    assert len(project.parse_errors) == 1
    assert project.parse_errors[0].file == str(bad)


def test_load_project_keeps_valid_modules_when_one_file_has_parse_error(tmp_path):
    good = tmp_path / "good.py"
    bad = tmp_path / "bad.py"

    good.write_text("x = 1\n", encoding="utf-8")
    bad.write_text("def x(:\n    pass\n", encoding="utf-8")

    project = load_project([str(good), str(bad)])

    assert len(project.modules) == 1
    assert len(project.parse_errors) == 1
    assert project.modules[0].filename == str(good)


def test_get_list_of_files_in_project_accepts_single_python_file(tmp_path):
    source = tmp_path / "a.py"
    source.write_text("x = 1\n", encoding="utf-8")

    files = get_list_of_files_in_project(str(source))

    assert files == [str(source)]


def test_get_list_of_files_in_project_recursively_finds_python_files(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("hello\n", encoding="utf-8")

    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.py").write_text("y = 2\n", encoding="utf-8")

    files = get_list_of_files_in_project(str(tmp_path))

    assert set(files) == {
        str(tmp_path / "a.py"),
        str(sub / "c.py"),
    }


def test_get_list_of_files_in_project_skips_venv_and_git_dirs(tmp_path):
    (tmp_path / "main.py").write_text("x = 1\n", encoding="utf-8")

    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()
    (venv_dir / "ignored.py").write_text("y = 2\n", encoding="utf-8")

    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "ignored2.py").write_text("z = 3\n", encoding="utf-8")

    files = get_list_of_files_in_project(str(tmp_path))

    assert str(tmp_path / "main.py") in files
    assert str(venv_dir / "ignored.py") not in files
    assert str(git_dir / "ignored2.py") not in files


def test_get_list_of_files_in_project_skips_private_prefixed_files(tmp_path):
    (tmp_path / "_hidden.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "visible.py").write_text("y = 2\n", encoding="utf-8")

    files = get_list_of_files_in_project(str(tmp_path))

    assert str(tmp_path / "visible.py") in files
    assert str(tmp_path / "_hidden.py") not in files


def test_get_list_of_files_in_project_raises_for_invalid_path(tmp_path):
    missing = tmp_path / "missing"

    with pytest.raises(FileNotFoundError):
        get_list_of_files_in_project(str(missing))


def test_resolve_project_root_for_multiple_files(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()

    a = pkg / "a.py"
    b = pkg / "b.py"
    a.write_text("x = 1\n", encoding="utf-8")
    b.write_text("y = 2\n", encoding="utf-8")

    root = resolve_project_root([str(a), str(b)])

    assert root == pkg.resolve()