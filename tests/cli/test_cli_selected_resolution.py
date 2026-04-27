from pathlib import Path

import pytest

from astanalyzer.cli import (
    build_parser,
    resolve_selected_cli_argument,
    resolve_selected_input,
)


def test_patch_parser_uses_positional_selected_json_path():
    parser = build_parser()

    args = parser.parse_args(["patch", "path/to/selected.json"])

    assert args.command == "patch"
    assert args.selected_json_path == "path/to/selected.json"
    assert args.deprecated_selected is None


def test_patch_parser_keeps_deprecated_selected_alias():
    parser = build_parser()

    args = parser.parse_args(["patch", "--selected", "path/to/selected.json"])

    assert args.command == "patch"
    assert args.selected_json_path is None
    assert args.deprecated_selected == "path/to/selected.json"


def test_selected_cli_argument_rejects_positional_and_deprecated_alias():
    with pytest.raises(SystemExit) as exc:
        resolve_selected_cli_argument("positional.json", "alias.json")

    assert exc.value.code == 2


def test_selected_cli_argument_accepts_deprecated_alias(caplog):
    resolved = resolve_selected_cli_argument(None, "alias.json")

    assert resolved == "alias.json"
    assert "--selected is deprecated" in caplog.text


def test_resolve_selected_input_prefers_astanalyzer_selected_json(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    preferred = tmp_path / "astanalyzer-selected.json"
    legacy = tmp_path / "selected.json"
    preferred.write_text("{}", encoding="utf-8")
    legacy.write_text("{}", encoding="utf-8")

    assert resolve_selected_input(copy_from_downloads=False) == preferred


def test_resolve_selected_input_can_be_optional(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    assert resolve_selected_input(copy_from_downloads=False, required=False) is None


def test_resolve_selected_explicit_path(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    f = tmp_path / "file.json"
    f.write_text("{}")

    result = resolve_selected_input(str(f))

    assert result == (project / "file.json").resolve()
    assert result.exists()
    assert not f.exists()


def test_resolve_selected_moves_from_downloads(tmp_path, monkeypatch):
    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    f = downloads / "astanalyzer-selected.json"
    f.write_text("{}")

    monkeypatch.setenv("HOME", str(tmp_path))

    cwd = tmp_path / "project"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    result = resolve_selected_input(None)

    assert result.exists()
    assert result.parent == cwd
    assert not f.exists()  


def test_archive_does_not_copy_from_downloads(tmp_path, monkeypatch):
    downloads = tmp_path / "Downloads"
    downloads.mkdir()

    f = downloads / "astanalyzer-selected.json"
    f.write_text("{}")

    monkeypatch.setenv("HOME", str(tmp_path))

    result = resolve_selected_input(
        None,
        copy_from_downloads=False,
        required=False,
    )

    assert result == f.resolve()
    assert f.exists()  # nesmí být smazán


def test_selected_cli_argument_conflict():
    with pytest.raises(SystemExit):
        resolve_selected_cli_argument("a.json", "b.json")


def test_selected_cli_argument_deprecated(caplog):
    resolve_selected_cli_argument(None, "a.json")

    assert "deprecated" in caplog.text.lower()


def test_archive_with_external_selected_file(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    external = tmp_path / "external.json"
    external.write_text("{}")

    result = resolve_selected_input(
        str(external),
        copy_from_downloads=True,
    )

    assert result.parent == project
