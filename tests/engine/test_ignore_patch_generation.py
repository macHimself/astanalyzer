from types import SimpleNamespace
from astanalyzer.engine.selected_patch_build import _build_ignore_fix_proposal
from astanalyzer.cli.utils.selected import resolve_selected_input

def make_match(lines, lineno):
    return SimpleNamespace(
        lineno=lineno,
        root=lambda: SimpleNamespace(
            file_by_lines=lines,
            file="test.py"
        )
    )


def test_ignore_module_level_creates_patch():
    match = make_match(["x = 1\n"], lineno=0)

    proposal = _build_ignore_fix_proposal(match, "STYLE-012")

    assert proposal is not None
    assert "ignore-next STYLE-012" in proposal.suggestion


def test_ignore_inserts_before_line():
    match = make_match(
        ["x = 1\n", "print(x)\n"],
        lineno=2
    )

    proposal = _build_ignore_fix_proposal(match, "STYLE-001")

    assert proposal is not None
    assert "ignore-next STYLE-001" in proposal.suggestion


def test_ignore_merges_existing_comment():
    match = make_match(
        ["# astanalyzer: ignore-next STYLE-001\n", "print('x')\n"],
        lineno=2
    )

    proposal = _build_ignore_fix_proposal(match, "STYLE-002")

    assert proposal is not None
    assert "STYLE-001, STYLE-002" in proposal.suggestion


from types import SimpleNamespace
from astanalyzer.engine.selected_patch_build import _build_ignore_fix_proposal


def test_ignore_module_level():
    match = SimpleNamespace(
        lineno=0,
        root=lambda: SimpleNamespace(
            file_by_lines=["x = 1\n"],
            file="a.py"
        )
    )

    proposal = _build_ignore_fix_proposal(match, "STYLE-012")

    assert proposal is not None
    assert "ignore-next STYLE-012" in proposal.suggestion


def test_archive_does_not_copy_from_downloads(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # ensure cwd is clean
    (tmp_path / "astanalyzer-selected.json").unlink(missing_ok=True)

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
