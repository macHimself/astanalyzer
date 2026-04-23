from pathlib import Path

from astanalyzer.cli import has_working_artifacts


def test_has_working_artifacts_returns_false_when_nothing_exists(tmp_path: Path):
    assert has_working_artifacts(tmp_path) is False


def test_has_working_artifacts_detects_report_file(tmp_path: Path):
    (tmp_path / "scan_report.json").write_text("{}", encoding="utf-8")
    assert has_working_artifacts(tmp_path) is True


def test_has_working_artifacts_detects_patch_file(tmp_path: Path):
    (tmp_path / "example.patch").write_text("dummy", encoding="utf-8")
    assert has_working_artifacts(tmp_path) is True
