from pathlib import Path

from astanalyzer.selection.file_selection import (
    filter_scan_paths,
    parse_excluded_dir_names,
    should_skip_path,
)


def test_parse_excluded_dir_names():
    assert parse_excluded_dir_names("tests, venv ,migrations") == {
        "tests",
        "venv",
        "migrations",
    }


def test_should_skip_path_returns_true_for_nested_tests_dir():
    path = Path("src/tests/unit/test_example.py")
    assert should_skip_path(path, {"tests"}) is True


def test_should_skip_path_returns_false_for_similar_name():
    path = Path("src/testing/example.py")
    assert should_skip_path(path, {"tests"}) is False


def test_filter_scan_paths_removes_paths_inside_excluded_dirs():
    paths = [
        Path("src/main.py"),
        Path("tests/test_main.py"),
        Path("src/module/helpers.py"),
        Path("migrations/0001_init.py"),
    ]
    result = filter_scan_paths(paths, {"tests", "migrations"})
    assert result == [
        Path("src/main.py"),
        Path("src/module/helpers.py"),
    ]
