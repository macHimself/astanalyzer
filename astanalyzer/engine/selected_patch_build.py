from __future__ import annotations

import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from colorama import init

from ..anchor import build_anchor
from ..fixer import FixProposal, fix
from ..ignore_rules import is_ignored_for_node
from ..rule import Rule

from .project_loader import ModuleNode, get_list_of_files_in_project, load_project
from .patch_writer import (
    present_foundings_suggestions,
    create_diff,
    emit_patch_if_changed,
)
from .reporting import _relpath
from .scan_runtime import prepare_rule_runtime, build_and_save_fixes

log = logging.getLogger(__name__)
init(autoreset=True)


def _resolve_selected_file_path2(file_value: str, base_dir: Path | None) -> Path:
    p = Path(file_value)
    if p.is_absolute():
        return p
    if base_dir is not None:
        return (base_dir / p).resolve()
    return p.resolve()


def _selected_fix_indexes(
    selected_data: dict[str, Any],
) -> tuple[
    dict[str, set[int]],
    dict[tuple[str | None, str | None, int | None, int | None, int | None, str | None], set[int]],
]:
    by_anchor_id: dict[str, set[int]] = defaultdict(set)
    by_fallback: dict[
        tuple[str | None, str | None, int | None, int | None, int | None, str | None],
        set[int],
    ] = defaultdict(set)

    findings = selected_data.get("findings", [])
    if not isinstance(findings, list):
        return by_anchor_id, by_fallback

    for finding in findings:
        rule_id = finding.get("rule_id")
        anchor = finding.get("anchor") or {}
        line = anchor.get("line", finding.get("start_line"))
        symbol_path = anchor.get("symbol_path")
        anchor_id = anchor.get("anchor_id")

        file_value = finding.get("file")
        end_line = anchor.get("end_line", finding.get("end_line"))
        col = anchor.get("col")

        fallback_key = (file_value, rule_id, line, end_line, col, symbol_path)

        selected_fix_list = finding.get("selected_fixes")
        if selected_fix_list is None:
            selected_fix_list = finding.get("fixes", []) or []

        for fix in selected_fix_list:
            fixer_index = fix.get("fixer_index")
            log.debug("SELECTED FIX raw=%s parsed_index=%s", fix, fixer_index)

            if fixer_index is None:
                continue

            by_fallback[fallback_key].add(fixer_index)

            if anchor_id:
                by_anchor_id[anchor_id].add(fixer_index)

    log.debug("SELECTED FIXES BY ANCHOR: %s", dict(by_anchor_id))
    log.debug("SELECTED FIXES BY FALLBACK: %s", dict(by_fallback))

    return by_anchor_id, by_fallback


def _selected_actions(
    selected_data: dict[str, Any],
) -> tuple[dict[str, list[dict[str, Any]]], dict[tuple, list[dict[str, Any]]]]:
    by_anchor_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_fallback: dict[tuple, list[dict[str, Any]]] = defaultdict(list)

    for action in selected_data.get("selected_actions", []) or []:
        if not isinstance(action, dict):
            continue

        anchor = action.get("anchor") or {}
        anchor_id = anchor.get("anchor_id")
        file_value = action.get("file") or anchor.get("file")
        rule_id = action.get("rule_id")
        line = anchor.get("line", action.get("start_line"))
        end_line = anchor.get("end_line", action.get("end_line"))
        col = anchor.get("col")
        symbol_path = anchor.get("symbol_path")

        fallback_key = (file_value, rule_id, line, end_line, col, symbol_path)

        if anchor_id:
            by_anchor_id[anchor_id].append(action)

        by_fallback[fallback_key].append(action)

    return by_anchor_id, by_fallback


def _build_ignore_next_comment(rule_ids: list[str]) -> str:
    seen = set()
    ordered: list[str] = []

    for rid in rule_ids:
        rid = (rid or "").strip()
        if not rid or rid in seen:
            continue
        seen.add(rid)
        ordered.append(rid)

    if not ordered:
        return "# astanalyzer: ignore-next"

    return "# astanalyzer: ignore-next " + ", ".join(ordered)


def _parse_ignore_next_line_ordered(line: str) -> list[str] | None:
    stripped = line.strip()

    if "astanalyzer:" not in stripped:
        return None

    try:
        _, rest = stripped.split("astanalyzer:", 1)
    except ValueError:
        return None

    rest = rest.strip()
    if not rest.startswith("ignore-next"):
        return None

    rest = rest[len("ignore-next"):].strip()
    if not rest:
        return []

    return [part.strip() for part in rest.split(",") if part.strip()]


def _merge_ignore_next_comment_line(line: str, rule_id: str) -> str | None:
    ids = _parse_ignore_next_line_ordered(line)
    if ids is None:
        return None

    if "*" in ids or rule_id in ids:
        return line

    merged = ids + [rule_id]

    indent = line[: len(line) - len(line.lstrip())]
    newline = "\n" if line.endswith("\n") else ""

    return indent + _build_ignore_next_comment(merged) + newline


def _build_ignore_fix_proposal(match, rule_id: str) -> FixProposal | None:
    root = match.root()
    lines = list(getattr(root, "file_by_lines", []) or [])
    filename = str(getattr(root, "file", "unknown.py"))
    lineno = getattr(match, "lineno", None)

    if not lines or lineno is None or lineno < 1:
        return None

    prev_index = lineno - 2

    # Case A: existing ignore-next directly above the node -> merge into that line
    if prev_index >= 0:
        prev_line = lines[prev_index]
        merged = _merge_ignore_next_comment_line(prev_line, rule_id)

        if merged is not None:
            if merged == prev_line:
                return None  # already present, nothing to do

            updated_lines = lines[:]
            updated_lines[prev_index] = merged

            return FixProposal(
                original="".join(lines),
                suggestion="".join(updated_lines),
                reason=f"Suppress finding {rule_id} for this node.",
                lineno=1,
                filename=filename,
                full_file_mode=True,
            )

    # Case B: no existing ignore-next -> reuse normal fixer builder
    builder = (
        fix()
        .insert_before(
            text=_build_ignore_next_comment([rule_id]),
        )
        .because(f"Suppress finding {rule_id} for this node.")
    )

    return builder.build(node=match)


def _emit_selected_actions_for_match(
    *,
    actions_for_match: list[dict[str, Any]],
    match,
    module: ModuleNode,
    patch_run_dir: Path | None,
    patch_counter: int,
    project_root: Path,
) -> int:
    for action in actions_for_match:
        action_type = action.get("type")

        if action_type != "ignore_finding":
            log.warning("Unsupported selected action type: %s", action_type)
            continue

        rule_id = action.get("rule_id")
        if not rule_id:
            log.warning("ignore_finding action missing rule_id: %s", action)
            continue

        fix_proposal = _build_ignore_fix_proposal(match, rule_id)
        if fix_proposal is None:
            continue

        present_foundings_suggestions(fix_proposal)
        create_diff(fix_proposal)

        out_path = emit_patch_if_changed(
            fix=fix_proposal,
            match=match,
            module=module,
            patch_run_dir=patch_run_dir,
            patch_index=patch_counter + 1,
            rule_id=f"{rule_id}-IGNORE",
            rule_title=f"Ignore {rule_id}",
            project_root=project_root,
        )

        if out_path is not None:
            patch_counter += 1

    return patch_counter


def build_patches_from_selected_json(
    selected_data: dict[str, Any],
    base_dir: Path | None = None,
) -> tuple[Path | None, int]:
    selected_fix_indexes_by_anchor_id, selected_fix_indexes_by_fallback = _selected_fix_indexes(
        selected_data
    )
    selected_actions_by_anchor_id, selected_actions_by_fallback = _selected_actions(
        selected_data
    )
    log.debug("PATCH BUILD START")

    findings = selected_data.get("findings", [])
    if not isinstance(findings, list):
        raise ValueError("'findings' must be a list")

    log.debug("Selected findings count: %d", len(findings))

    files: list[Path] = []
    seen = set()

    for item in findings + (selected_data.get("selected_actions", []) or []):
        file_value = item.get("file")
        if not file_value:
            anchor = item.get("anchor") or {}
            file_value = anchor.get("file")

        log.debug("Selected item file value: %s", file_value)

        if not file_value:
            continue

        p = Path(file_value)
        if not p.is_absolute() and base_dir is not None:
            p = (base_dir / p).resolve()

        log.debug("Resolved file path: %s", p)

        if p not in seen:
            files.append(p)
            seen.add(p)

    if not files:
        log.warning("No files selected")
        return None, 0

    if len(files) == 1:
        scan_root = files[0].parent.resolve()
    else:
        scan_root = Path(os.path.commonpath([str(p) for p in files])).resolve()
        if scan_root.is_file():
            scan_root = scan_root.parent

    log.debug("Derived scan root: %s", scan_root)

    all_project_files = [Path(p).resolve() for p in get_list_of_files_in_project(str(scan_root))]
    log.debug("Project files to load: %s", all_project_files)

    if not all_project_files:
        log.warning("No project files found under scan root: %s", scan_root)
        return None, 0

    for p in all_project_files:
        try:
            text = p.read_text(encoding="utf-8")
            if not text.endswith("\n"):
                p.write_text(text + "\n", encoding="utf-8")
                log.info("Added final newline to project file: %s", p)
        except Exception as e:
            log.warning("Failed to normalize final newline for %s: %s", p, e)

    project = load_project([str(p) for p in all_project_files])
    project.root_dir = scan_root

    _, rule_index, project_root, patch_run_dir = prepare_rule_runtime(project, build_fixes=True)

    log.debug("Rule index size: %d", len(rule_index))
    log.debug("Patch output directory: %s", patch_run_dir)

    patch_counter = 0

    selected_anchor_ids = set()
    fallback_keys = set()
    selected_action_anchor_ids = set()
    selected_action_fallback_keys = set()

    for f in findings:
        anchor = f.get("anchor") or {}
        anchor_id = anchor.get("anchor_id")

        if anchor_id:
            selected_anchor_ids.add(anchor_id)

        fallback = (
            f.get("file"),
            f.get("rule_id"),
            anchor.get("line", f.get("start_line")),
            anchor.get("end_line", f.get("end_line")),
            anchor.get("col"),
            anchor.get("symbol_path"),
        )
        fallback_keys.add(fallback)

        log.debug("Selected anchor: id=%s fallback=%s", anchor_id, fallback)

    for action in selected_data.get("selected_actions", []) or []:
        anchor = action.get("anchor") or {}
        anchor_id = anchor.get("anchor_id")

        if anchor_id:
            selected_action_anchor_ids.add(anchor_id)

        fallback = (
            action.get("file") or anchor.get("file"),
            action.get("rule_id"),
            anchor.get("line", action.get("start_line")),
            anchor.get("end_line", action.get("end_line")),
            anchor.get("col"),
            anchor.get("symbol_path"),
        )
        selected_action_fallback_keys.add(fallback)

        log.debug("Selected action anchor: id=%s fallback=%s", anchor_id, fallback)


    log.debug("Anchor IDs loaded: %d", len(selected_anchor_ids))

    for module, node in project.walk_all_nodes():
        node_type = node.__class__.__name__
        rules_for_type = rule_index.get(node_type, [])

        if not rules_for_type:
            continue

        rel_file = _relpath(Path(module.filename))

        log.debug(
            "Node: %s in %s rules=%d",
            node_type,
            rel_file,
            len(rules_for_type),
        )

        for rule in rules_for_type:
            rid = getattr(rule, "id", None) or rule.__class__.__name__

            matches = rule.match_node(
                node,
                ctx={"module": module, "project": project},
            )

            if not matches:
                continue

            log.debug("Rule %s matched %d nodes", rid, len(matches))

            for match_result in matches:
                match = match_result.node
                refs = match_result.refs

                log.debug(
                    "PATCH MATCH rule=%s line=%s end_line=%s col=%s id=%s",
                    rid,
                    getattr(match, "lineno", None),
                    getattr(match, "end_lineno", None),
                    getattr(match, "col_offset", None),
                    id(match),
                )

                anchor = build_anchor(
                    rule_id=rid,
                    file_path=rel_file,
                    match=match,
                )

                log.debug(
                    "Computed anchor: id=%s line=%s symbol=%s",
                    anchor.anchor_id,
                    getattr(match, "lineno", None),
                    getattr(anchor, "symbol_path", None),
                )

                fallback = (
                    rel_file,
                    rid,
                    getattr(match, "lineno", None),
                    getattr(match, "end_lineno", getattr(match, "lineno", None)),
                    getattr(match, "col_offset", None),
                    getattr(anchor, "symbol_path", None),
                )

                selected_indexes_for_match = None
                actions_for_match: list[dict[str, Any]] = []

                matched_selected_fix = False
                matched_selected_action = False

                if anchor.anchor_id in selected_anchor_ids:
                    log.debug("Anchor matched selected fix by ID")
                    matched_selected_fix = True
                    selected_indexes_for_match = selected_fix_indexes_by_anchor_id.get(anchor.anchor_id)

                elif fallback in fallback_keys:
                    log.debug("Anchor matched selected fix by fallback")
                    matched_selected_fix = True
                    selected_indexes_for_match = selected_fix_indexes_by_fallback.get(fallback)

                if anchor.anchor_id in selected_action_anchor_ids:
                    log.debug("Anchor matched selected action by ID")
                    matched_selected_action = True
                    actions_for_match = selected_actions_by_anchor_id.get(anchor.anchor_id, [])

                elif fallback in selected_action_fallback_keys:
                    log.debug("Anchor matched selected action by fallback")
                    matched_selected_action = True
                    actions_for_match = selected_actions_by_fallback.get(fallback, [])

                log.debug(
                    "SELECTION CHECK file=%s rule=%s anchor_id=%s line=%s end_line=%s col=%s fallback=%s anchor_hit=%s fallback_hit=%s",
                    rel_file,
                    rid,
                    anchor.anchor_id,
                    getattr(match, "lineno", None),
                    getattr(match, "end_lineno", None),
                    getattr(match, "col_offset", None),
                    fallback,
                    anchor.anchor_id in selected_anchor_ids,
                    fallback in fallback_keys,
                )

                if not matched_selected_fix and not matched_selected_action:
                    log.debug(
                        "MATCH SKIPPED file=%s rule=%s line=%s end_line=%s col=%s symbol=%s",
                        rel_file,
                        rid,
                        getattr(match, "lineno", None),
                        getattr(match, "end_lineno", None),
                        getattr(match, "col_offset", None),
                        getattr(anchor, "symbol_path", None),
                    )
                    continue

                if is_ignored_for_node(rid, match):
                    log.debug(
                        "[SKIP IGNORE] file=%s rule=%s line=%s",
                        rel_file,
                        rid,
                        getattr(match, "lineno", None),
                    )
                    continue
                if matched_selected_fix:
                    log.info(
                        "Generating patch for %s:%s rule=%s selected_fixers=%s",
                        rel_file,
                        getattr(match, "lineno", "?"),
                        rid,
                        selected_indexes_for_match,
                    )

                    patch_counter = build_and_save_fixes(
                        rule=rule,
                        match=match,
                        refs=refs,
                        module=module,
                        project=project,
                        project_root=project_root,
                        patch_run_dir=patch_run_dir,
                        patch_counter=patch_counter,
                        selected_fixer_indexes=selected_indexes_for_match,
                    )

                if matched_selected_action and actions_for_match:
                    log.info(
                        "Generating selected actions for %s:%s rule=%s actions=%s",
                        rel_file,
                        getattr(match, "lineno", "?"),
                        rid,
                        [a.get("type") for a in actions_for_match],
                    )

                    patch_counter = _emit_selected_actions_for_match(
                        actions_for_match=actions_for_match,
                        match=match,
                        module=module,
                        patch_run_dir=patch_run_dir,
                        patch_counter=patch_counter,
                        project_root=project_root,
                    )

    log.info("PATCH BUILD FINISHED patches=%d", patch_counter)
    return patch_run_dir, patch_counter
