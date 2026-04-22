"""
Rule execution and reporting pipeline for project analysis.

This module coordinates the main analysis workflow over a loaded project.
It is responsible for:

- indexing rules by node type
- walking parsed AST nodes
- evaluating matching rules
- building findings and optional fix plans
- generating patch outputs when fixes are enabled
- producing aggregated analysis reports and scan JSON output

The functions in this module form the bridge between parsed project data,
rule evaluation, fix generation, and final reporting.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List

from colorama import init

from ..anchor import build_anchor
from ..fixer import FixProposal
from ..ignore_rules import is_ignored_for_node
from ..rule import Rule

from .project_loader import ProjectNode, ModuleNode, count_lines
from .reporting import Finding, AnalysisReport, build_scan_json, _relpath
from .patch_writer import (
    present_foundings_suggestions,
    create_diff,
    emit_patch_if_changed,
    build_patch_preview_data
)

log = logging.getLogger(__name__)


def attach_fix_preview_overrides(
    *,
    finding: Finding,
    rule,
    match,
    refs: dict[str, Any] | None,
    module: ModuleNode,
    project: ProjectNode,
    project_root: Path,
) -> None:
    """Build preview-only diff metadata for each fixer builder attached to a finding."""
    for fixer_index, fixer in enumerate(getattr(rule, "fixer_builders", []) or []):
        try:
            result = fixer.build(
                node=match,
                module=module,
                project=project,
                project_root=project_root,
                refs=refs or {},
            )
            fixes = [] if result is None else (result if isinstance(result, list) else [result])
            preview_data = build_patch_preview_data(fixes)
            if preview_data:
                finding.fix_preview_overrides[fixer_index] = preview_data
        except Exception as exc:
            finding.fix_preview_overrides[fixer_index] = {
                "patch_preview": "",
                "patch_preview_status": "unavailable",
                "patch_preview_error": str(exc),
            }


def build_rule_index_by_node_type(rules):
    """
    Build a lookup index mapping AST node type names to matching rules.

    The index is populated from rule matchers and optional `node_type`
    declarations to speed up rule dispatch during project traversal.
    """
    index = defaultdict(list)

    def add(rule, t: str):
        t = (t or "").strip()
        if not t:
            return
        if rule not in index[t]:
            index[t].append(rule)

    for rule in rules:
        matchers = []
        if getattr(rule, "matcher", None):
            matchers.append(rule.matcher)
        matchers.extend(getattr(rule, "matchers", []) or [])

        for m in matchers:
            et = getattr(m, "expected_type", None)
            if isinstance(et, str) and et:
                for t in et.split("|"):
                    add(rule, t)

        nt = getattr(rule, "node_type", None)
        if isinstance(nt, (list, tuple, set)):
            for t in nt:
                if isinstance(t, str):
                    add(rule, t)

    return dict(index)


def debug_walk(project: ProjectNode, limit=10):
    """
    Log a short preview of traversed AST nodes for debugging purposes.
    """
    for i, (module, node) in enumerate(project.walk_all_nodes()):
        if i >= limit:
            break
        node_type = node.__class__.__name__
        lineno = getattr(node, "lineno", "?")
        log.debug("%s %s %s", module.filename, lineno, node_type)


def profile_analysis(enabled: bool = False):
    """
    Return a decorator that measures and logs function execution time.

    When disabled, the original function is returned unchanged.
    """
    def decorator(fn):
        if not enabled:
            return fn

        @wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = fn(*args, **kwargs)
            duration = time.perf_counter() - start
            log.info("[PROFILE] %s took %.3f s", fn.__name__, duration)
            return result

        return wrapper

    return decorator


def prepare_rule_runtime(project: ProjectNode, build_fixes: bool):
    """
    Prepare shared runtime state for rule execution.

    Returns loaded rules, rule index, resolved project root, and patch
    output configuration used during analysis.
    """
    rules = list(Rule.registry)
    rule_index = build_rule_index_by_node_type(rules)

    project_root = getattr(project, "root_dir", None)
    if not project_root:
        raise ValueError("ProjectNode.root_dir is not set")

    project_root = Path(project_root).resolve()
    patch_run_dir = 1  # make_patch_run_dir(project_root) if build_fixes else None

    return rules, rule_index, project_root, patch_run_dir


def extract_code_snippet(
    file_path: str | Path,
    start_line: int | None,
    end_line: int | None,
    context: int = 4,
) -> tuple[str | None, int | None, int | None, bool]:
    if start_line is None:
        return None, None, None, False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        total = len(lines)
        match_end = end_line if end_line else start_line

        snippet_start = max(1, start_line - context)
        snippet_end = min(total, match_end + context)

        original_snippet_start = snippet_start

        max_backtrack = 20
        attempts = 0

        while attempts < max_backtrack and snippet_start > 1:
            snippet = "".join(lines[snippet_start - 1:snippet_end])

            triple_double_count = snippet.count('"""')
            triple_single_count = snippet.count("'''")

            nonempty_lines = [line.strip() for line in snippet.splitlines() if line.strip()]
            first_nonempty = nonempty_lines[0] if nonempty_lines else ""

            suspicious_start = first_nonempty in {'"""', "'''"}
            odd_triple_state = (
                triple_double_count % 2 == 1
                or triple_single_count % 2 == 1
            )

            if not suspicious_start and not odd_triple_state:
                break

            snippet_start -= 1
            attempts += 1

        snippet_lines = lines[snippet_start - 1:snippet_end]

        trim_index = None
        scan_limit = min(6, len(snippet_lines))

        first_nonempty_idx = None
        for idx, line in enumerate(snippet_lines):
            if line.strip():
                first_nonempty_idx = idx
                break

        if first_nonempty_idx is not None:
            first_nonempty = snippet_lines[first_nonempty_idx].strip()

            if not first_nonempty.startswith((
                "def ", "class ", "if ", "for ", "while ",
                "try:", "with ", "match ", "@", "return ",
                "import ", "from ", "#"
            )):
                for idx in range(scan_limit):
                    stripped = snippet_lines[idx].strip()
                    if stripped in {'"""', "'''"}:
                        trim_index = idx + 1
                        break

        if trim_index is not None and trim_index < len(snippet_lines):
            snippet_lines = snippet_lines[trim_index:]
            snippet_start += trim_index

        snippet = "".join(snippet_lines)
        snippet_truncated = snippet_start > 1 or original_snippet_start > 1

        return snippet, snippet_start, snippet_end, snippet_truncated

    except Exception:
        return None, None, None, False
    

def build_finding(rule, match, module: ModuleNode, project_root: Path | None = None) -> Finding:
    """
    Build a normalized finding object from a matched rule result.

    The finding includes rule metadata, source location, message,
    and a stable anchor used for later identification.
    """
    rid = getattr(rule, "id", None) or rule.__class__.__name__
    cat = getattr(rule, "category", "uncategorized")
    sev = getattr(rule, "severity", "info")
    title = getattr(rule, "title", None) or rid

    file_str = (
        _relpath(Path(module.filename), project_root=project_root)
        if project_root is not None
        else Path(module.filename).as_posix()
    )

    anchor = build_anchor(
        rule_id=rid,
        file_path=file_str,
        match=match,
    )

    msg = getattr(match, "message", None)
    if not msg:
        msg = getattr(rule, "description", None)
    if not msg:
        msg = title
    if not msg:
        msg = f"{rid} matched {match.__class__.__name__}"

    line = getattr(match, "lineno", None)
    end_line = getattr(match, "end_lineno", line)

    code_snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        module.filename,
        line,
        end_line,
        context=4,
    )

    return Finding(
        file=Path(module.filename),
        rule_id=rid,
        category=cat,
        severity=sev,
        title=title,
        line=line,
        end_line=end_line,
        message=getattr(match, "message", msg),
        code_snippet=code_snippet,
        snippet_start_line=snippet_start,
        snippet_end_line=snippet_end,
        snippet_truncated=snippet_truncated,
        anchor=anchor,
    )


def attach_fixers_to_finding(finding: Finding, rule) -> None:
    """Attach rule-defined fixer builders to a finding as available fix options."""
    for fixer in getattr(rule, "fixer_builders", []) or []:
        finding.fixes.append(fixer)


def build_and_save_fixes(
    *,
    rule,
    match,
    refs: dict[str, Any] | None,
    module: ModuleNode,
    project: ProjectNode,
    project_root: Path,
    patch_run_dir: Path | None,
    patch_counter: int,
    selected_fixer_indexes: set[int] | None = None,
) -> int:
    """
    Build fix proposals for a matched rule and emit patch files when applicable.

    Only valid `FixProposal` objects are processed. Generated suggestions are
    previewed, diffed, and optionally written as patch files. The updated patch
    counter is returned.
    """
    rid = getattr(rule, "id", rule.__class__.__name__)
    title = getattr(rule, "title", None) or rid

    for fixer_index, fixer in enumerate(getattr(rule, "fixer_builders", []) or []):
        if selected_fixer_indexes is not None and fixer_index not in selected_fixer_indexes:
            continue

        try:
            result = fixer.build(
                node=match,
                module=module,
                project=project,
                project_root=project_root,
                refs=refs or {},
            )

            if result is None:
                continue

            fixes = result if isinstance(result, list) else [result]

            for fix in fixes:
                if not isinstance(fix, FixProposal):
                    log.warning(
                        "[FixUI] Skipping non-FixProposal result for rule %s: %r",
                        rid,
                        type(fix).__name__,
                    )
                    continue

                present_foundings_suggestions(fix)
                create_diff(fix)

                out_path = emit_patch_if_changed(
                    fix=fix,
                    match=match,
                    module=module,
                    patch_run_dir=patch_run_dir,
                    patch_index=patch_counter + 1,
                    rule_id=rid,
                    project_root=project_root,
                )

                if out_path is not None:
                    patch_counter += 1

        except Exception as e:
            log.warning("[FixUI] Skipping patch emit for rule %s: %s", rid, e)

    return patch_counter


def process_rule_matches(
    *,
    rule,
    node,
    module: ModuleNode,
    project: ProjectNode,
    project_root: Path,
    build_plans: bool,
    build_fixes: bool,
    patch_run_dir: Path | None,
    patch_counter: int,
) -> tuple[List[Finding], int]:
    """
    Process all matches of a single rule on a single AST node.

    Builds findings, skips ignored matches, optionally attaches fix plans,
    and optionally generates patch files.
    """
    findings: List[Finding] = []

    matches = rule.match_node(node, ctx={"module": module, "project": project})
    if not matches:
        return findings, patch_counter

    rid = getattr(rule, "id", None) or rule.__class__.__name__
    log.debug("[MATCH] %s", rid)

    for match_result in matches:
        match = match_result.node
        refs = match_result.refs

        if is_ignored_for_node(rid, match):
            log.debug(
                "[IGNORED] rule=%s file=%s line=%s",
                rid,
                module.filename,
                getattr(match, "lineno", None),
            )
            continue

        finding = build_finding(rule, match, module, project_root=project_root)

        if build_plans:
            attach_fixers_to_finding(finding, rule)
            attach_fix_preview_overrides(
                finding=finding,
                rule=rule,
                match=match,
                refs=refs,
                module=module,
                project=project,
                project_root=project_root,
            )

        if build_fixes:
            patch_counter = build_and_save_fixes(
                rule=rule,
                match=match,
                refs=refs,
                module=module,
                project=project,
                project_root=project_root,
                patch_run_dir=patch_run_dir,
                patch_counter=patch_counter,
                selected_fixer_indexes=None,
            )

        findings.append(finding)

    return findings, patch_counter


def run_rules_on_project_one_pass(
    project: ProjectNode,
    build_plans: bool = True,
    build_fixes: bool = False,
) -> List[Finding]:
    """
    Run all indexed rules over the project in a single AST traversal pass.

    Returns the list of collected findings.
    """
    findings: List[Finding] = []

    _, rule_index, project_root, patch_run_dir = prepare_rule_runtime(project, build_fixes)
    patch_counter = 0

    for module, node in project.walk_all_nodes():
        node_type = node.__class__.__name__
        rules_for_type = rule_index.get(node_type, [])

        if rules_for_type:
            log.debug("[NODE_RULES] %s, %s", node_type, [r.id for r in rules_for_type])

        for rule in rules_for_type:
            new_findings, patch_counter = process_rule_matches(
                rule=rule,
                node=node,
                module=module,
                project=project,
                project_root=project_root,
                build_plans=build_plans,
                build_fixes=build_fixes,
                patch_run_dir=patch_run_dir,
                patch_counter=patch_counter,
            )
            findings.extend(new_findings)

    return findings


@profile_analysis(enabled=True)
def run_rules_on_project_report(
    project: ProjectNode,
    build_plans=True,
    build_fixes=False,
) -> tuple[AnalysisReport, dict[str, Any]]:
    """
    Run project analysis and return both aggregated report data and scan JSON.

    The report includes timing and line metrics, while the JSON output is
    normalized for UI and export workflows.
    """
    report = AnalysisReport()
    report.start()

    for module in project.modules:
        path = Path(module.filename)
        report.add_file(path, count_lines(path))

    findings = run_rules_on_project_one_pass(
        project,
        build_plans=build_plans,
        build_fixes=build_fixes,
    )

    project_root = getattr(project, "root_dir", None)
    if not project_root:
        raise ValueError("ProjectNode.root_dir is not set")

    report.add_findings(findings)
    report.stop()

    return report, build_scan_json(findings, project_root=Path(project_root))


def run_rules_on_project_scan_json(project: ProjectNode) -> Dict[str, Any]:
    """
    Run project analysis and return only normalized scan JSON output.
    """
    findings = run_rules_on_project_one_pass(project, build_plans=True, build_fixes=False)

    project_root = getattr(project, "root_dir", None)
    if not project_root:
        raise ValueError("ProjectNode.root_dir is not set")

    return build_scan_json(findings, project_root=Path(project_root))
