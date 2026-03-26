#!/usr/bin/env python3
"""
Command-line interface for astanalyzer.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .engine import (
    build_patches_from_selected_json,
    get_list_of_files_in_project,
    load_project,
    run_rules_on_project_report,
)
from .logging_config import setup_logging
from .report_ui import open_report_in_browser, write_report_html
from .rule_loader import import_rules_from_path
from .rules import load_builtin_rules

log = logging.getLogger(__name__)


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def get_archive_root(base_dir: Path | None = None) -> Path:
    root = base_dir or Path.cwd()
    archive_root = root / "used_runs"
    archive_root.mkdir(parents=True, exist_ok=True)
    return archive_root


def create_run_archive_dir(base_dir: Path | None = None) -> Path:
    archive_dir = get_archive_root(base_dir) / now_stamp()
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir


def find_patch_files_from_cwd() -> list[Path]:
    return sorted(p for p in Path.cwd().rglob("*.patch") if p.is_file())


def move_file_if_exists(src: Path, dst_dir: Path) -> Path | None:
    if not src.exists() or not src.is_file():
        return None

    dst = dst_dir / src.name
    src.rename(dst)
    log.info("Archived: %s -> %s", src, dst)
    return dst


def archive_run_artifacts(archive_dir: Path, base_dir: Path | None = None) -> list[Path]:
    root = base_dir or Path.cwd()
    archived: list[Path] = []

    candidates = [
        root / "astanalyzer-selected.json",
        root / "selected.json",
        root / "scan_report.json",
        root / "report.html",
    ]

    for p in candidates:
        out = move_file_if_exists(p, archive_dir)
        if out is not None:
            archived.append(out)

    return archived


def archive_patch_files_from_cwd(archive_dir: Path, base_dir: Path | None = None) -> int:
    root = base_dir or Path.cwd()
    patch_files = find_patch_files_from_cwd()

    if not patch_files:
        return 0

    patches_root = archive_dir / "patches"
    moved = 0

    for patch in patch_files:
        rel_patch = patch.relative_to(root)
        dst = patches_root / rel_patch
        dst.parent.mkdir(parents=True, exist_ok=True)
        patch.rename(dst)
        moved += 1
        log.info("Archived patch: %s -> %s", patch, dst)

    return moved


def clean_working_artifacts(
    include_archive: bool = False,
    base_dir: Path | None = None,
) -> tuple[int, list[Path]]:
    root = base_dir or Path.cwd()
    removed = 0
    removed_paths: list[Path] = []

    log.debug("Starting clean in: %s", root)

    normal_files = [
        root / "astanalyzer-selected.json",
        root / "selected.json",
        root / "scan_report.json",
        root / "report.html",
    ]

    for p in normal_files:
        if p.exists() and p.is_file():
            log.debug("Removing file: %s", p)
            p.unlink()
            removed += 1
            removed_paths.append(p)
        else:
            log.debug("Skipping (not found): %s", p)

    for patch in root.rglob("*.patch"):
        if patch.is_file():
            log.debug("Removing patch: %s", patch)
            patch.unlink()
            removed += 1
            removed_paths.append(patch)

    if include_archive:
        archive_root = root / "used_runs"
        if archive_root.exists() and archive_root.is_dir():
            log.debug("Removing archive directory: %s", archive_root)
            shutil.rmtree(archive_root)
            removed += 1
            removed_paths.append(archive_root)
        else:
            log.debug("No archive directory found: %s", archive_root)

    return removed, removed_paths


def resolve_selected_input(
    selected_arg: str | None = None,
    *,
    copy_from_downloads: bool = True,
) -> Path:
    """
    Resolve selected findings JSON from:
    1. explicit CLI path
    2. working directory
    3. newest matching file in ~/Downloads
    """
    if selected_arg:
        p = Path(selected_arg).expanduser().resolve()
        if not p.exists():
            log.error("Selected file '%s' doesn't exist.", p)
            sys.exit(1)
        if not p.is_file():
            log.error("Selected path '%s' is not a file.", p)
            sys.exit(1)
        return p

    cwd = Path.cwd()

    local_candidates = [
        cwd / "selected.json",
        cwd / "astanalyzer-selected.json",
    ]
    for candidate in local_candidates:
        if candidate.exists() and candidate.is_file():
            log.info("Using selected JSON from working directory: %s", candidate)
            return candidate

    downloads = Path.home() / "Downloads"
    if not downloads.exists() or not downloads.is_dir():
        log.error(
            "Downloads directory '%s' does not exist and no local selected JSON was found.",
            downloads,
        )
        sys.exit(1)

    candidates = sorted(
        downloads.glob("astanalyzer-selected*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not candidates:
        log.error(
            "No selected JSON found in working directory or Downloads "
            "(looked for 'selected.json', 'astanalyzer-selected.json', "
            "and '~/Downloads/astanalyzer-selected*.json')."
        )
        sys.exit(1)

    newest = candidates[0]

    if not copy_from_downloads:
        log.info("Using selected JSON directly from Downloads: %s", newest)
        return newest.resolve()

    target = cwd / newest.name

    if target.exists():
        try:
            same_file = target.resolve() == newest.resolve()
        except FileNotFoundError:
            same_file = False

        if same_file:
            log.info("Selected JSON already available in working directory: %s", target)
            return target

        log.warning("Overwriting existing file in working directory: %s", target)

    shutil.copy2(newest, target)
    if newest.exists():
        newest.unlink()

    log.info("Copied selected JSON from Downloads: %s -> %s", newest, target)
    return target.resolve()


def ensure_final_newline(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        path.write_text(text + "\n", encoding="utf-8")


def collect_selected_files(
    selected_data: dict[str, Any],
    base_dir: Path | None = None,
) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()

    findings = selected_data.get("findings", [])
    if not isinstance(findings, list):
        return files

    for finding in findings:
        file_value = finding.get("file")
        if not file_value:
            continue

        p = Path(file_value)
        if not p.is_absolute() and base_dir is not None:
            p = (base_dir / p).resolve()
        else:
            p = p.resolve()

        if p not in seen:
            seen.add(p)
            files.append(p)

    return files


def validate_path(str_path: str) -> Path:
    path = Path(str_path)
    if not path.exists():
        log.error("Path '%s' doesn't exist.", path)
        sys.exit(1)

    log.info("Existing path: %s", path)
    return path


def check_all_patches_from_cwd() -> tuple[int, int]:
    root = Path.cwd()
    patch_files = find_patch_files_from_cwd()

    if not patch_files:
        print("No patch files found.")
        return 0, 0

    ok = 0
    failed = 0

    print()
    print("=" * 60)
    print("ASTANALYZER PATCH CHECK")
    print(f"Root: {root}")
    print(f"Patches found: {len(patch_files)}")

    for patch in patch_files:
        rel_patch = patch.relative_to(root)
        patch_dir = patch.parent

        result = subprocess.run(
            ["git", "apply", "--check", patch.name],
            cwd=patch_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            ok += 1
            print(f"[OK]   {rel_patch}")
        else:
            failed += 1
            print(f"[FAIL] {rel_patch}")
            if result.stderr.strip():
                print(result.stderr.strip())

    return ok, failed


def apply_all_patches_from_cwd() -> tuple[int, int]:
    root = Path.cwd()
    patch_files = find_patch_files_from_cwd()

    if not patch_files:
        print("No patch files found.")
        return 0, 0

    ok = 0
    failed = 0

    print()
    print("=" * 60)
    print("ASTANALYZER PATCH APPLY")
    print(f"Root: {root}")
    print(f"Patches found: {len(patch_files)}")

    for patch in patch_files:
        rel_patch = patch.relative_to(root)
        patch_dir = patch.parent

        result = subprocess.run(
            ["git", "apply", patch.name],
            cwd=patch_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            ok += 1
            print(f"[OK]   {rel_patch}")
        else:
            failed += 1
            print(f"[FAIL] {rel_patch}")
            if result.stderr.strip():
                print(result.stderr.strip())

    return ok, failed


def cmd_scan(args) -> None:
    path = validate_path(args.path)
    files = get_list_of_files_in_project(str(path))
    project = load_project(files)
    report, scan = run_rules_on_project_report(project, True, False)

    json_path = Path("scan_report.json").resolve()
    json_path.write_text(
        json.dumps(scan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info("Scan report JSON saved to: %s", json_path)

    html_path = Path("report.html").resolve()
    write_report_html(scan, html_path)
    log.info("Scan report HTML saved to: %s", html_path)

    if not args.no_open:
        open_report_in_browser(html_path)
        log.info("Report opened in browser.")

    print()
    print("=" * 60)
    print("ASTANALYZER SCAN SUMMARY")
    print(report.to_text())
    print()


def cmd_report(args) -> None:
    report_path = validate_path(args.path)
    open_report_in_browser(report_path)
    log.info("Report opened in browser: %s", report_path)


def cmd_patch(args) -> None:
    selected = resolve_selected_input(args.selected)

    try:
        data = json.loads(selected.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        log.error("Invalid JSON in '%s': %s", selected, exc)
        sys.exit(1)

    selected_files = collect_selected_files(data, base_dir=selected.parent)
    for path in selected_files:
        ensure_final_newline(path)

    _, patch_count = build_patches_from_selected_json(
        data,
        base_dir=selected.parent,
    )

    if patch_count == 0:
        print("No patches were generated.")
        return

    ok, failed = check_all_patches_from_cwd()

    print()
    print("=" * 60)
    print("ASTANALYZER PATCH SUMMARY")
    print(f"Patches generated: {patch_count}")
    print(f"Patch checks OK:   {ok}")
    print(f"Patch checks FAIL: {failed}")
    print()


def cmd_apply(args) -> None:
    patch_files = find_patch_files_from_cwd()

    if not patch_files:
        print("No patch files found. Nothing to apply.")
        return

    ok, failed = check_all_patches_from_cwd()

    print()
    print("=" * 60)
    print("ASTANALYZER APPLY CHECK SUMMARY")
    print(f"Patches found:     {len(patch_files)}")
    print(f"Patch checks OK:   {ok}")
    print(f"Patch checks FAIL: {failed}")

    if failed > 0:
        print("Apply aborted because some patches failed check.")
        print()
        return

    apply_ok, apply_failed = apply_all_patches_from_cwd()

    print()
    print("=" * 60)
    print("ASTANALYZER APPLY SUMMARY")
    print(f"Patch apply OK:    {apply_ok}")
    print(f"Patch apply FAIL:  {apply_failed}")

    if apply_failed > 0:
        print("Archive skipped because some patch applies failed.")
        print()
        return

    archive_dir = create_run_archive_dir(Path.cwd())

    archived_files = archive_run_artifacts(
        archive_dir=archive_dir,
        base_dir=Path.cwd(),
    )
    archived_patches = archive_patch_files_from_cwd(
        archive_dir=archive_dir,
        base_dir=Path.cwd(),
    )

    print()
    print("=" * 60)
    print("ASTANALYZER FINALIZE")
    print(f"Archive dir:       {archive_dir}")
    print(f"Archived files:    {len(archived_files)}")
    print(f"Archived patches:  {archived_patches}")
    print()


def cmd_clean(args) -> None:
    if args.include_archive:
        confirm = input("Delete archive too? [y/N]: ")
        if confirm.lower() != "y":
            print("Aborted.")
            return

    removed_count, removed_paths = clean_working_artifacts(
        include_archive=args.include_archive,
        base_dir=Path.cwd(),
    )

    print()
    print("=" * 60)
    print("ASTANALYZER CLEAN SUMMARY")
    print(f"Removed items: {removed_count}")

    if removed_count == 0:
        print("Nothing to clean.")

    if args.verbose_list:
        print("\nRemoved items:")
        for p in removed_paths:
            print(f" - {p}")
    print()


def add_rules_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--rules",
        action="append",
        default=[],
        help="Path to a custom rule file or directory. Can be used multiple times.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="astanalyzer static analysis tool"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v, -vv)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Show only errors",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    report_parser = subparsers.add_parser("report", help="Open existing HTML report")
    report_parser.add_argument(
        "path",
        nargs="?",
        default="report.html",
        help="Path to HTML report",
    )
    report_parser.set_defaults(func=cmd_report)

    clean_parser = subparsers.add_parser("clean", help="Delete working artefacts and patches")
    clean_parser.add_argument(
        "--include-archive",
        action="store_true",
        help="Delete the used_runs archive too",
    )
    clean_parser.add_argument(
        "--verbose-list",
        action="store_true",
        help="Print all removed files",
    )
    clean_parser.set_defaults(func=cmd_clean)

    scan_parser = subparsers.add_parser("scan", help="Run project scan")
    scan_parser.add_argument(
        "path",
        help="Path to a Python file or directory",
    )
    scan_parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open HTML report automatically after scan",
    )
    add_rules_argument(scan_parser)
    scan_parser.set_defaults(func=cmd_scan)

    patch_parser = subparsers.add_parser("patch", help="Generate patches from selected fixes")
    patch_parser.add_argument(
        "selected",
        nargs="?",
        default=None,
        help="Selected fixes JSON file; if missing, uses local file or newest from Downloads",
    )
    patch_parser.set_defaults(func=cmd_patch)

    apply_parser = subparsers.add_parser("apply", help="Apply existing .patch files")
    apply_parser.set_defaults(func=cmd_apply)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.quiet:
        log_level = "ERROR"
    elif args.verbose == 0:
        log_level = "WARNING"
    elif args.verbose == 1:
        log_level = "INFO"
    else:
        log_level = "DEBUG"

    setup_logging(log_level)

    load_builtin_rules()

    for rules_path in getattr(args, "rules", []):
        imported = import_rules_from_path(rules_path)
        log.info("Imported %d custom rule file(s) from %s", len(imported), rules_path)

    log.info("astanalyzer started")
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())