from pathlib import Path

from astanalyzer.cli import cmd_archive


class Args:
    pass


def test_cmd_archive_moves_reports_and_patches(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    (tmp_path / "scan_report.json").write_text("{}", encoding="utf-8")
    (tmp_path / "report.html").write_text("<html></html>", encoding="utf-8")
    (tmp_path / "astanalyzer-selected.json").write_text("{}", encoding="utf-8")
    (tmp_path / "a.py__STYLE-010__0001.patch").write_text("diff", encoding="utf-8")

    cmd_archive(Args())

    archive_root = tmp_path / "used_patches"
    archives = list(archive_root.iterdir())

    assert len(archives) == 1
    archive_dir = archives[0]

    assert (archive_dir / "scan_report.json").exists()
    assert (archive_dir / "report.html").exists()
    assert (archive_dir / "astanalyzer-selected.json").exists()
    assert (archive_dir / "patches" / "a.py__STYLE-010__0001.patch").exists()

    assert not (tmp_path / "scan_report.json").exists()
    assert not (tmp_path / "report.html").exists()
    assert not (tmp_path / "astanalyzer-selected.json").exists()
    assert not (tmp_path / "a.py__STYLE-010__0001.patch").exists()




def test_cmd_archive_does_nothing_when_no_artifacts_exist(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    cmd_archive(Args())
    captured = capsys.readouterr()

    assert "Nothing to archive." in captured.out
    assert not (tmp_path / "used_patches").exists()