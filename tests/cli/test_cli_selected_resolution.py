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
