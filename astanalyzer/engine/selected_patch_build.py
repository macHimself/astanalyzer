from __future__ import annotations

import logging
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..anchor import build_anchor
from ..fixer import FixProposal, fix
from ..ignore_rules import is_ignored_for_node

from .project_loader import ModuleNode, ProjectNode, get_list_of_files_in_project, load_project
from .patch_writer import (
    create_diff,
    emit_patch_if_changed,
    present_foundings_suggestions,
)
from .reporting import _relpath
from .scan_runtime import build_and_save_fixes, prepare_rule_runtime

log = logging.getLogger(__name__)


FallbackKey = tuple[str | None, str | None, int | None, int | None, int | None, str | None]


def _anchor_dict(item: dict[str, Any]) -> dict[str, Any]:
    return item.get("anchor") or {}


def _fallback_key(
    *,
    file_value: str | None,
    rule_id: str | None,
    line: int | None,
    end_line: int | None,
    col: int | None,
    symbol_path: str | None,
) -> FallbackKey:
    return (file_value, rule_id, line, end_line, col, symbol_path)


def _selected_fix_indexes(
    selected_data: dict[str, Any],
) -> tuple[dict[str, set[int]], dict[FallbackKey, set[int]]]:
    by_anchor_id: dict[str, set[int]] = defaultdict(set)
    by_fallback: dict[FallbackKey, set[int]] = defaultdict(set)

    findings = selected_data.get("findings", [])
    if not isinstance(findings, list):
        return by_anchor_id, by_fallback

    for finding in findings:
        anchor = _anchor_dict(finding)
        anchor_id = anchor.get("anchor_id")

        fallback = _fallback_key(
            file_value=finding.get("file"),
            rule_id=finding.get("rule_id"),
            line=anchor.get("line", finding.get("start_line")),
            end_line=anchor.get("end_line", finding.get("end_line")),
            col=anchor.get("col"),
            symbol_path=anchor.get("symbol_path"),
        )

        selected_fix_list = finding.get("selected_fixes")
        if selected_fix_list is None:
            selected_fix_list = finding.get("fixes", []) or []

        for fix in selected_fix_list:
            fixer_index = fix.get("fixer_index")
            log.debug("SELECTED FIX raw=%s parsed_index=%s", fix, fixer_index)

            if fixer_index is None:
                continue

            by_fallback[fallback].add(fixer_index)
            if anchor_id:
                by_anchor_id[anchor_id].add(fixer_index)

    log.debug("SELECTED FIXES BY ANCHOR: %s", dict(by_anchor_id))
    log.debug("SELECTED FIXES BY FALLBACK: %s", dict(by_fallback))
    return by_anchor_id, by_fallback


def _selected_actions(
    selected_data: dict[str, Any],
) -> tuple[dict[str, list[dict[str, Any]]], dict[FallbackKey, list[dict[str, Any]]]]:
    by_anchor_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_fallback: dict[FallbackKey, list[dict[str, Any]]] = defaultdict(list)

    for action in selected_data.get("selected_actions", []) or []:
        if not isinstance(action, dict):
            continue

        anchor = _anchor_dict(action)
        anchor_id = anchor.get("anchor_id")

        fallback = _fallback_key(
            file_value=action.get("file") or anchor.get("file"),
            rule_id=action.get("rule_id"),
            line=anchor.get("line", action.get("start_line")),
            end_line=anchor.get("end_line", action.get("end_line")),
            col=anchor.get("col"),
            symbol_path=anchor.get("symbol_path"),
        )

        if anchor_id:
            by_anchor_id[anchor_id].append(action)

        by_fallback[fallback].append(action)

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

    if prev_index >= 0:
        prev_line = lines[prev_index]
        merged = _merge_ignore_next_comment_line(prev_line, rule_id)

        if merged is not None:
            if merged == prev_line:
                return None

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

    builder = (
        fix()
        .insert_before(text=_build_ignore_next_comment([rule_id]))
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


@dataclass
class SelectedPatchLookup:
    selected_anchor_ids: set[str]
    fallback_keys: set[FallbackKey]
    selected_action_anchor_ids: set[str]
    selected_action_fallback_keys: set[FallbackKey]
    selected_fix_indexes_by_anchor_id: dict[str, set[int]]
    selected_fix_indexes_by_fallback: dict[FallbackKey, set[int]]
    selected_actions_by_anchor_id: dict[str, list[dict[str, Any]]]
    selected_actions_by_fallback: dict[FallbackKey, list[dict[str, Any]]]


def _get_selected_findings(selected_data: dict[str, Any]) -> list[dict[str, Any]]:
    findings = selected_data.get("findings", [])
    if not isinstance(findings, list):
        raise ValueError("'findings' must be a list")
    return findings


def _collect_selected_files(
    findings: list[dict[str, Any]],
    selected_actions: list[dict[str, Any]],
    base_dir: Path | None,
) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()

    for item in findings + selected_actions:
        file_value = item.get("file")
        if not file_value:
            file_value = _anchor_dict(item).get("file")

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

    return files


def _derive_scan_root(files: list[Path]) -> Path | None:
    if not files:
        return None

    if len(files) == 1:
        return files[0].parent.resolve()

    scan_root = Path(os.path.commonpath([str(p) for p in files])).resolve()
    if scan_root.is_file():
        scan_root = scan_root.parent
    return scan_root


def _normalize_final_newlines(paths: list[Path]) -> None:
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8")
            if not text.endswith("\n"):
                p.write_text(text + "\n", encoding="utf-8")
                log.info("Added final newline to project file: %s", p)
        except Exception as e:
            log.warning("Failed to normalize final newline for %s: %s", p, e)


def _load_patch_build_project(scan_root: Path) -> ProjectNode | None:
    all_project_files = [Path(p).resolve() for p in get_list_of_files_in_project(str(scan_root))]
    log.debug("Project files to load: %s", all_project_files)

    if not all_project_files:
        log.warning("No project files found under scan root: %s", scan_root)
        return None

    _normalize_final_newlines(all_project_files)

    project = load_project([str(p) for p in all_project_files])
    project.root_dir = scan_root
    return project


def _build_selected_patch_lookup(
    *,
    findings: list[dict[str, Any]],
    selected_actions: list[dict[str, Any]],
    selected_fix_indexes_by_anchor_id: dict[str, set[int]],
    selected_fix_indexes_by_fallback: dict[FallbackKey, set[int]],
    selected_actions_by_anchor_id: dict[str, list[dict[str, Any]]],
    selected_actions_by_fallback: dict[FallbackKey, list[dict[str, Any]]],
) -> SelectedPatchLookup:
    selected_anchor_ids: set[str] = set()
    fallback_keys: set[FallbackKey] = set()
    selected_action_anchor_ids: set[str] = set()
    selected_action_fallback_keys: set[FallbackKey] = set()

    for finding in findings:
        anchor = _anchor_dict(finding)
        anchor_id = anchor.get("anchor_id")

        if anchor_id:
            selected_anchor_ids.add(anchor_id)

        fallback = _fallback_key(
            file_value=finding.get("file"),
            rule_id=finding.get("rule_id"),
            line=anchor.get("line", finding.get("start_line")),
            end_line=anchor.get("end_line", finding.get("end_line")),
            col=anchor.get("col"),
            symbol_path=anchor.get("symbol_path"),
        )
        fallback_keys.add(fallback)

        log.debug("Selected anchor: id=%s fallback=%s", anchor_id, fallback)

    for action in selected_actions:
        anchor = _anchor_dict(action)
        anchor_id = anchor.get("anchor_id")

        if anchor_id:
            selected_action_anchor_ids.add(anchor_id)

        fallback = _fallback_key(
            file_value=action.get("file") or anchor.get("file"),
            rule_id=action.get("rule_id"),
            line=anchor.get("line", action.get("start_line")),
            end_line=anchor.get("end_line", action.get("end_line")),
            col=anchor.get("col"),
            symbol_path=anchor.get("symbol_path"),
        )
        selected_action_fallback_keys.add(fallback)

        log.debug("Selected action anchor: id=%s fallback=%s", anchor_id, fallback)

    return SelectedPatchLookup(
        selected_anchor_ids=selected_anchor_ids,
        fallback_keys=fallback_keys,
        selected_action_anchor_ids=selected_action_anchor_ids,
        selected_action_fallback_keys=selected_action_fallback_keys,
        selected_fix_indexes_by_anchor_id=selected_fix_indexes_by_anchor_id,
        selected_fix_indexes_by_fallback=selected_fix_indexes_by_fallback,
        selected_actions_by_anchor_id=selected_actions_by_anchor_id,
        selected_actions_by_fallback=selected_actions_by_fallback,
    )


def _resolve_selected_match(
    *,
    anchor_id: str,
    fallback: FallbackKey,
    lookup: SelectedPatchLookup,
) -> tuple[bool, bool, set[int] | None, list[dict[str, Any]]]:
    selected_indexes_for_match = None
    actions_for_match: list[dict[str, Any]] = []

    matched_selected_fix = False
    matched_selected_action = False

    if anchor_id in lookup.selected_anchor_ids:
        log.debug("Anchor matched selected fix by ID")
        matched_selected_fix = True
        selected_indexes_for_match = lookup.selected_fix_indexes_by_anchor_id.get(anchor_id)
    elif fallback in lookup.fallback_keys:
        log.debug("Anchor matched selected fix by fallback")
        matched_selected_fix = True
        selected_indexes_for_match = lookup.selected_fix_indexes_by_fallback.get(fallback)

    if anchor_id in lookup.selected_action_anchor_ids:
        log.debug("Anchor matched selected action by ID")
        matched_selected_action = True
        actions_for_match = lookup.selected_actions_by_anchor_id.get(anchor_id, [])
    elif fallback in lookup.selected_action_fallback_keys:
        log.debug("Anchor matched selected action by fallback")
        matched_selected_action = True
        actions_for_match = lookup.selected_actions_by_fallback.get(fallback, [])

    return (
        matched_selected_fix,
        matched_selected_action,
        selected_indexes_for_match,
        actions_for_match,
    )


def _process_selected_match(
    *,
    rule,
    match_result,
    module: ModuleNode,
    project: ProjectNode,
    project_root: Path,
    patch_run_dir: Path | None,
    patch_counter: int,
    rel_file: str,
    lookup: SelectedPatchLookup,
) -> int:
    rid = getattr(rule, "id", None) or rule.__class__.__name__
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

    fallback = _fallback_key(
        file_value=rel_file,
        rule_id=rid,
        line=getattr(match, "lineno", None),
        end_line=getattr(match, "end_lineno", getattr(match, "lineno", None)),
        col=getattr(match, "col_offset", None),
        symbol_path=getattr(anchor, "symbol_path", None),
    )

    matched_selected_fix, matched_selected_action, selected_indexes_for_match, actions_for_match = (
        _resolve_selected_match(
            anchor_id=anchor.anchor_id,
            fallback=fallback,
            lookup=lookup,
        )
    )

    log.debug(
        "SELECTION CHECK file=%s rule=%s anchor_id=%s line=%s end_line=%s col=%s fallback=%s anchor_hit=%s fallback_hit=%s",
        rel_file,
        rid,
        anchor.anchor_id,
        getattr(match, "lineno", None),
        getattr(match, "end_lineno", None),
        getattr(match, "col_offset", None),
        fallback,
        anchor.anchor_id in lookup.selected_anchor_ids,
        fallback in lookup.fallback_keys,
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
        return patch_counter

    if is_ignored_for_node(rid, match):
        log.debug(
            "[SKIP IGNORE] file=%s rule=%s line=%s",
            rel_file,
            rid,
            getattr(match, "lineno", None),
        )
        return patch_counter

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

    findings = _get_selected_findings(selected_data)
    selected_actions = selected_data.get("selected_actions", []) or []

    log.debug("Selected findings count: %d", len(findings))

    files = _collect_selected_files(findings, selected_actions, base_dir)
    if not files:
        log.warning("No files selected")
        return None, 0

    scan_root = _derive_scan_root(files)
    if scan_root is None:
        log.warning("No scan root could be derived")
        return None, 0

    log.debug("Derived scan root: %s", scan_root)

    project = _load_patch_build_project(scan_root)
    if project is None:
        return None, 0

    _, rule_index, project_root, patch_run_dir = prepare_rule_runtime(project, build_fixes=True)

    log.debug("Rule index size: %d", len(rule_index))
    log.debug("Patch output directory: %s", patch_run_dir)

    lookup = _build_selected_patch_lookup(
        findings=findings,
        selected_actions=selected_actions,
        selected_fix_indexes_by_anchor_id=selected_fix_indexes_by_anchor_id,
        selected_fix_indexes_by_fallback=selected_fix_indexes_by_fallback,
        selected_actions_by_anchor_id=selected_actions_by_anchor_id,
        selected_actions_by_fallback=selected_actions_by_fallback,
    )

    log.debug("Anchor IDs loaded: %d", len(lookup.selected_anchor_ids))

    patch_counter = 0

    for module, node in project.walk_all_nodes():
        node_type = node.__class__.__name__
        rules_for_type = rule_index.get(node_type, [])

        if not rules_for_type:
            continue

        rel_file = _relpath(Path(module.filename))

        log.debug("Node: %s in %s rules=%d", node_type, rel_file, len(rules_for_type))

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
                patch_counter = _process_selected_match(
                    rule=rule,
                    match_result=match_result,
                    module=module,
                    project=project,
                    project_root=project_root,
                    patch_run_dir=patch_run_dir,
                    patch_counter=patch_counter,
                    rel_file=rel_file,
                    lookup=lookup,
                )

    log.info("PATCH BUILD FINISHED patches=%d", patch_counter)
    return patch_run_dir, patch_counter
