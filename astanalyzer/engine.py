from __future__ import annotations

import csv
import io
import json
import logging
import os
import re
import textwrap
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from astroid import nodes, parse
from astroid.exceptions import AstroidSyntaxError
from colorama import Fore, Style, init

from .anchor import FindingAnchor, build_anchor
from .fixer import FixProposal, fix
from .ignore_rules import is_ignored_for_node
from .rule import Rule

log = logging.getLogger(__name__)
init(autoreset=True)


def _syntax_loc(err):
    """
    Extract line/column from SyntaxError or AstroidSyntaxError.

    Astroid may hide the original syntax error inside ``__cause__``.
    """
    base = getattr(err, "__cause__", None) or err
    lineno = getattr(base, "lineno", None)
    col = getattr(base, "offset", None)
    return lineno, col


def get_list_of_files_in_project(location: str) -> List[str]:
    """
    Collect Python files from a single file path or recursively from a directory.
    """
    skip_dirs = {".git", ".venv", "venv", "UPOL", "dist", "build", "__pycache__"}
    file_list: List[str] = []

    if os.path.isfile(location) and location.endswith(".py"):
        file_list.append(location)
    elif os.path.isdir(location):
        for root, dirs, files in os.walk(location):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith("_")]
            for file in files:
                if file.endswith(".py") and not file.startswith("_"):
                    file_list.append(os.path.join(root, file))
    else:
        raise FileNotFoundError(
            f"Input path '{location}' is not a valid Python file or directory."
        )

    return file_list


def git_root(start: Path | None = None) -> Path:
    """
    Find git root by walking up to the first directory containing ``.git``.
    """
    p = (start or Path.cwd()).resolve()

    for parent in [p, *p.parents]:
        if (parent / ".git").exists():
            return parent

    return Path.cwd()


def _slug(s: str, max_len: int = 60) -> str:
    """
    Convert text to a filesystem-safe slug.
    """
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:max_len] or "run"


def make_patch_run_dir(project_root: Path) -> Path:
    """
    Create a directory for patch artefacts under ``.astanalyzer/patches``.
    """
    base = project_root / ".astanalyzer" / "patches"
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = base / f"{ts}__{_slug(project_root.name)}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_patch(
    *,
    patch_run_dir: Path,
    rule_id: str,
    rel_file: str,
    index: int,
    patch_text: str,
) -> Path:
    """
    Write a patch next to the source file.

    ``patch_run_dir`` is currently ignored to preserve old behaviour.
    """
    source_path = Path(rel_file)

    if not source_path.is_absolute():
        source_path = (Path.cwd() / source_path).resolve()
    else:
        source_path = source_path.resolve()

    patch_name = f"{source_path.name}__{rule_id}__{index:04d}.patch"
    out = source_path.with_name(patch_name)
    out.write_text(patch_text, encoding="utf-8")
    return out


@dataclass
class Finding:
    """
    Represents a single rule finding detected during a project scan.
    """

    file: Path
    rule_id: str
    category: str
    severity: str = "info"
    title: Optional[str] = None
    line: Optional[int] = None
    end_line: Optional[int] = None
    message: Optional[str] = None
    fixes: List[Any] = field(default_factory=list)
    anchor: FindingAnchor | None = None


class ModuleNode:
    """
    Parsed Python module wrapper.
    """

    def __init__(self, filename: str, ast_root: nodes.Module):
        self.filename = filename
        self.ast_root = ast_root


@dataclass(frozen=True)
class ParseError:
    file: str
    message: str
    lineno: Optional[int] = None
    col_offset: Optional[int] = None
    error_type: str = "PARSE_ERROR"


class ProjectNode:
    """
    Container for parsed project modules and AST traversal helpers.
    """

    def __init__(self):
        self.modules: List[ModuleNode] = []
        self.root_dir: Path | None = None
        self.parse_errors: List[ParseError] = []

    def add_module(self, module: ModuleNode) -> None:
        self.modules.append(module)

    def add_parse_error(self, filepath: str, message: str, lineno=None, col_offset=None):
        self.parse_errors.append(
            ParseError(
                file=filepath,
                message=message,
                lineno=lineno,
                col_offset=col_offset,
            )
        )

    def walk_astroid_tree(self, node: nodes.NodeNG):
        yield node
        try:
            children = node.get_children()
        except Exception:
            return
        for child in children:
            yield from self.walk_astroid_tree(child)

    def walk_all_nodes(self):
        for module in self.modules:
            root = module.ast_root
            for node in self.walk_astroid_tree(root):
                yield module, node

    def walk_all_nodes_visual(self):
        for module in self.modules:
            root = module.ast_root
            for node in self.walk_astroid_tree(root):
                node_type = node.__class__.__name__
                lineno = getattr(node, "lineno", "?")
                name = (
                    getattr(node, "name", None)
                    or getattr(node, "attrname", None)
                    or getattr(node, "id", None)
                    or ""
                )
                log.debug("%s:%s -> %s %s", module.filename, lineno, node_type, name)
                yield node_type


def resolve_project_root(project_files: List[str]) -> Path | None:
    if not project_files:
        return None

    common = Path(os.path.commonpath(project_files)).resolve()

    if common.is_file() or common.suffix == ".py":
        return git_root(common.parent)

    return common


def read_source_file(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def parse_source(filepath: str, code: str) -> nodes.Module:
    return parse(code, module_name=str(filepath))


def attach_tree_metadata(tree: nodes.Module, filepath: str, code: str) -> None:
    tree.file = filepath
    tree.file_content = code
    tree.file_by_lines = code.splitlines(keepends=True)


def handle_parse_exception(
    project: ProjectNode,
    filepath: str,
    code: str,
    exc: Exception,
) -> None:
    base = getattr(exc, "__cause__", None) or exc
    lineno, col = _syntax_loc(exc)

    snippet = ""
    if lineno is not None:
        lines = code.splitlines()
        if 1 <= lineno <= len(lines):
            bad_line = lines[lineno - 1]
            caret = " " * max((col or 1) - 1, 0) + "^"
            snippet = f"\n    {bad_line}\n    {caret}"

    log.warning(
        "Syntax error in %s:%s:%s: %s%s",
        filepath,
        lineno,
        col,
        base,
        snippet,
    )

    project.add_parse_error(
        filepath=filepath,
        message=str(base),
        lineno=lineno,
        col_offset=col,
    )


def load_single_module(filepath: str) -> ModuleNode:
    code = read_source_file(filepath)
    tree = parse_source(filepath, code)
    attach_tree_metadata(tree, filepath, code)
    return ModuleNode(filename=filepath, ast_root=tree)


def load_project(project_files: List[str]) -> ProjectNode:
    project = ProjectNode()
    project.root_dir = resolve_project_root(project_files)

    for filepath in project_files:
        try:
            code = read_source_file(filepath)
        except OSError as e:
            project.add_parse_error(filepath, str(e))
            continue

        try:
            tree = parse_source(filepath, code)
        except (SyntaxError, IndentationError, AstroidSyntaxError) as e:
            handle_parse_exception(project, filepath, code, e)
            continue

        attach_tree_metadata(tree, filepath, code)
        project.add_module(ModuleNode(filename=filepath, ast_root=tree))

    return project


def present_foundings_suggestions(fix: FixProposal) -> None:
    """
    Print a formatted debug preview of a proposed fix.
    """
    if log.isEnabledFor(logging.DEBUG):
        lines = []

        lines.append("Suggested Fix:")
        lines.append("-" * 60)

        for i, line in enumerate(fix.suggestion.splitlines()):
            lineno_str = str(fix.lineno + i).rjust(4)
            lines.append(f" {lineno_str} | {line}")

        lines.append("-" * 60)
        lines.append("Reason:")
        lines.append(textwrap.fill(fix.reason, width=70))
        lines.append("-" * 60)

        log.debug("\n".join(lines))


def _format_colored_diff(diff_text: str) -> str:
    lines: list[str] = []

    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            lines.append(Fore.GREEN + line + Style.RESET_ALL)
        elif line.startswith("-") and not line.startswith("---"):
            lines.append(Fore.RED + line + Style.RESET_ALL)
        elif line.startswith("@@"):
            lines.append(Fore.CYAN + line + Style.RESET_ALL)
        else:
            lines.append(line)

    return "\n".join(lines)


def create_diff(fix: FixProposal) -> None:
    """
    Generate unified diff text for a fix proposal and store it on the object.
    """
    diff_text = fix.get_diff()
    fix.diff = diff_text

    log.debug(
        "DIFF for %s:%s\n%s",
        fix.filename,
        fix.lineno,
        _format_colored_diff(diff_text),
    )


@dataclass
class RuleResult:
    """
    Minimal intermediate result of evaluating a single rule on a node.
    """

    rule_id: str
    category: str
    lineno: Optional[int]
    message: str


@dataclass
class AnalysisReport:
    """
    Aggregates analysis metrics and findings for a single scan run.
    """

    files_analyzed: int = 0
    lines_analyzed: int = 0
    findings: List[Finding] = field(default_factory=list)
    _t0: float = field(default=0.0, init=False, repr=False)
    _t1: float = field(default=0.0, init=False, repr=False)

    def start(self) -> None:
        self._t0 = time.perf_counter()

    def stop(self) -> None:
        self._t1 = time.perf_counter()

    @property
    def elapsed(self) -> float:
        return max(0.0, (self._t1 or time.time()) - self._t0)

    def add_file(self, path: Path, line_count: int) -> None:
        self.files_analyzed += 1
        self.lines_analyzed += line_count

    def add_findings(self, items: Iterable[Finding]) -> None:
        self.findings.extend(items)

    def to_text(self) -> str:
        by_cat: Dict[str, int] = {}
        for f in self.findings:
            by_cat[f.category] = by_cat.get(f.category, 0) + 1

        cat_str = (
            ", ".join(
                f"{k}={v}"
                for k, v in sorted(by_cat.items(), key=lambda kv: (-kv[1], kv[0]))
            )
            or "—"
        )

        e = self.elapsed
        if e < 0.005:
            speed = "—"
        else:
            speed = f"{self.lines_analyzed / e:.0f} LOC/s"

        return (
            "=" * 60
            + "\n"
            + f"Analyzed {self.files_analyzed} files, {self.lines_analyzed} lines of code.\n"
            + f"Found {len(self.findings)} matches ({cat_str}).\n"
            + f"Execution time: {self.elapsed:.2f}s (≈ {speed})\n"
            + "=" * 60
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(
            {
                "files": self.files_analyzed,
                "lines": self.lines_analyzed,
                "matches_total": len(self.findings),
                "time_seconds": round(self.elapsed, 3),
                "findings": [
                    {
                        "file": str(f.file),
                        "rule_id": f.rule_id,
                        "category": f.category,
                        "line": f.line,
                        "message": f.message,
                        "anchor": asdict(f.anchor) if f.anchor else None,
                        "fixes": [
                            {
                                **fixer_to_fix_dict(fixer, fix_id=f"FX-{i + 1:03d}-A"),
                                "fixer_index": i,
                            }
                            for i, fixer in enumerate(f.fixes)
                        ],
                    }
                    for f in self.findings
                ],
            },
            ensure_ascii=False,
            indent=indent,
        )

    def to_csv(self) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["file", "line", "rule_id", "category", "message", "anchor_id"])
        for f in self.findings:
            writer.writerow(
                [
                    str(f.file),
                    f.line or "",
                    f.rule_id,
                    f.category,
                    f.message or "",
                    f.anchor.anchor_id if f.anchor else "",
                ]
            )
        return buf.getvalue()

    def save_csv(self, path: Path) -> None:
        path.write_text(self.to_csv(), encoding="utf-8")


def count_lines(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def convert_results(filename: str, results: Iterable[RuleResult]) -> List[Finding]:
    p = Path(filename)
    out: List[Finding] = []
    for r in results:
        out.append(
            Finding(
                file=p,
                rule_id=r.rule_id,
                category=r.category,
                line=getattr(r, "lineno", None),
                message=getattr(r, "message", None),
            )
        )
    return out


def fixer_to_fix_dict(fixer: Any, fix_id: str) -> Dict[str, Any]:
    """
    Convert a fixer builder into a normalized fix dictionary for report JSON.
    """
    dsl: Optional[Dict[str, Any]] = None

    if hasattr(fixer, "to_dict") and callable(fixer.to_dict):
        payload = fixer.to_dict()
        dsl = payload.get("dsl") if isinstance(payload, dict) else None
        title = payload.get("title") if isinstance(payload, dict) else None
        reason = payload.get("reason") if isinstance(payload, dict) else None
    else:
        title = getattr(fixer, "title", None)
        reason = getattr(fixer, "reason", None)

    if dsl is None and hasattr(fixer, "dsl"):
        maybe = getattr(fixer, "dsl")
        if isinstance(maybe, dict):
            dsl = maybe

    if dsl is None and hasattr(fixer, "to_json") and callable(fixer.to_json):
        try:
            maybe = json.loads(fixer.to_json())
            if isinstance(maybe, dict):
                dsl = maybe.get("dsl") if "dsl" in maybe else maybe
        except Exception:
            dsl = None

    if dsl is None:
        reason_parts = getattr(fixer, "reason_parts", None) or []
        if not reason and reason_parts:
            reason = "; ".join(reason_parts)
        dsl = {"because": reason or "—", "actions": []}

    return {
        "fix_id": fix_id,
        "title": title or "Proposed fix",
        "reason": reason or "—",
        "dsl": dsl,
    }


def build_rule_index_by_node_type(rules):
    """
    Build an index of rules keyed by AST node type names.
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


def plan_to_fix_dict(fixer: Any, fix_id: str) -> Dict[str, Any]:
    """
    Backward-compatible alias for converting a plan/fixer to normalized JSON.
    """
    return fixer_to_fix_dict(fixer, fix_id=fix_id)


def _relpath(p: Path, root: Path | None = None) -> str:
    try:
        cwd = Path.cwd().resolve()
        return p.resolve().relative_to(cwd).as_posix()
    except Exception:
        return p.as_posix()


def build_scan_json(findings: List[Finding], project_root: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {"findings": []}

    f_counter = 0
    fx_counter = 0

    for f in findings:
        f_counter += 1
        finding_id = f"F-{f_counter:03d}"

        start_line = f.line or 1
        end_line = f.end_line or start_line

        fixes = []
        for fixer_index, fixer in enumerate(f.fixes or []):
            fx_counter += 1
            fix_id = f"FX-{fx_counter:03d}-A"
            item = fixer_to_fix_dict(fixer, fix_id=fix_id)
            item["fixer_index"] = fixer_index
            fixes.append(item)

        out["findings"].append(
            {
                "id": finding_id,
                "rule_id": f.rule_id,
                "title": f.title or f.rule_id,
                "severity": f.severity,
                "file": _relpath(f.file, project_root),
                "start_line": start_line,
                "end_line": end_line,
                "message": f.message or "",
                "anchor": asdict(f.anchor) if f.anchor else None,
                "fixes": fixes,
            }
        )
    return out


def debug_walk(project: ProjectNode, limit=10):
    for i, (module, node) in enumerate(project.walk_all_nodes()):
        if i >= limit:
            break
        node_type = node.__class__.__name__
        lineno = getattr(node, "lineno", "?")
        log.debug("%s %s %s", module.filename, lineno, node_type)


def profile_analysis2(enabled: bool = False):
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
    rules = list(Rule.registry)
    rule_index = build_rule_index_by_node_type(rules)

    project_root = getattr(project, "root_dir", None)
    if not project_root:
        raise ValueError("ProjectNode.root_dir is not set")

    project_root = Path(project_root).resolve()
    patch_run_dir = 1  # make_patch_run_dir(project_root) if build_fixes else None

    return rules, rule_index, project_root, patch_run_dir


def build_finding(rule, match, module: ModuleNode, project_root: Path | None = None) -> Finding:
    rid = getattr(rule, "id", None) or rule.__class__.__name__
    cat = getattr(rule, "category", "uncategorized")
    sev = getattr(rule, "severity", "info")
    title = getattr(rule, "title", None) or rid

    file_str = (
        _relpath(Path(module.filename), project_root)
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

    return Finding(
        file=Path(module.filename),
        rule_id=rid,
        category=cat,
        severity=sev,
        title=title,
        line=getattr(match, "lineno", None),
        end_line=getattr(match, "end_lineno", getattr(match, "lineno", None)),
        message=getattr(match, "message", msg),
        anchor=anchor,
    )


def attach_fixers_to_finding(finding: Finding, rule) -> None:
    for fixer in getattr(rule, "fixer_builders", []) or []:
        finding.fixes.append(fixer)


def resolve_fix_line_range(fix, match) -> tuple[int, int]:
    sline = getattr(fix, "lineno", None)
    eline = getattr(fix, "end_lineno", None)

    if sline is None:
        sline = getattr(match, "lineno", 1)
    if eline is None:
        eline = getattr(match, "end_lineno", sline)

    if getattr(fix, "suggestion", "") in ("", None) and eline > sline:
        eline = sline

    return sline, eline


def emit_patch_if_changed(
    *,
    fix: FixProposal,
    match,
    module: ModuleNode,
    patch_run_dir: Path | None,
    patch_index: int,
    rule_id: str,
    rule_title: str,
    project_root: Path,
) -> Path | None:
    if patch_run_dir is None:
        return None

    if not isinstance(fix, FixProposal):
        return None

    if fix.suggestion == fix.original:
        return None

    resolve_fix_line_range(fix, match)

    rel_file = _relpath(
        Path(getattr(fix, "filename", module.filename)),
        project_root,
    )

    return write_patch(
        patch_run_dir=patch_run_dir,
        rule_id=rule_id,
        rel_file=rel_file,
        index=patch_index,
        patch_text=fix.get_diff(),
    )


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
                    rule_title=title,
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


@profile_analysis2(enabled=True)
def run_rules_on_project_report(
    project: ProjectNode,
    build_plans=True,
    build_fixes=False,
) -> tuple[AnalysisReport, dict[str, Any]]:
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
    findings = run_rules_on_project_one_pass(project, build_plans=True, build_fixes=False)

    project_root = getattr(project, "root_dir", None)
    if not project_root:
        raise ValueError("ProjectNode.root_dir is not set")

    return build_scan_json(findings, project_root=Path(project_root))


def _resolve_selected_file_path(file_value: str, base_dir: Path | None) -> Path:
    p = Path(file_value)
    if p.is_absolute():
        return p
    if base_dir is not None:
        return (base_dir / p).resolve()
    return p.resolve()


def _selected_anchor_keys(
    selected_data: dict[str, Any],
) -> tuple[
    dict[str, set[str]],
    dict[str, set[tuple[str, int | None, str | None]]],
]:
    by_file_anchor_id: dict[str, set[str]] = defaultdict(set)
    by_file_fallback: dict[str, set[tuple[str, int | None, str | None]]] = defaultdict(set)

    findings = selected_data.get("findings", [])
    if not isinstance(findings, list):
        return by_file_anchor_id, by_file_fallback

    for finding in findings:
        file_value = finding.get("file")
        if not file_value:
            continue

        anchor = finding.get("anchor") or {}
        rule_id = finding.get("rule_id")
        line = anchor.get("line", finding.get("start_line"))
        symbol_path = anchor.get("symbol_path")

        anchor_id = anchor.get("anchor_id")
        if anchor_id:
            by_file_anchor_id[file_value].add(anchor_id)

        by_file_fallback[file_value].add((rule_id, line, symbol_path))

    return by_file_anchor_id, by_file_fallback


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
