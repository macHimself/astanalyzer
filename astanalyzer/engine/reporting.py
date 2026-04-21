"""
Reporting models and serialization helpers for analysis results.

This module defines lightweight data structures representing findings,
rule evaluation results, and aggregated scan reports. It also provides
helpers for converting fix builders into normalized report data and for
serializing analysis output to text, JSON, and CSV formats.
"""
from __future__ import annotations

import csv
import io
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from ..anchor import FindingAnchor
from .path_utils import to_project_relative_path

@dataclass
class Finding:
    """
    Structured representation of a single issue detected during analysis.

    A finding describes where the issue was found, which rule produced it,
    how severe it is, and which optional fixes or anchors are associated with it.
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


@dataclass
class RuleResult:
    """
    Minimal intermediate result produced when a rule matches a node.

    This lightweight structure is later converted into a full `Finding`
    object for reporting.
    """

    rule_id: str
    category: str
    lineno: Optional[int]
    message: str


@dataclass
class AnalysisReport:
    """
    Aggregated report for a single analysis run.

    Tracks basic scan metrics such as analyzed files, lines of code,
    elapsed time, and all findings collected during the run. The report
    can be exported in text, JSON, and CSV forms.
    """

    files_analyzed: int = 0
    lines_analyzed: int = 0
    findings: List[Finding] = field(default_factory=list)
    _t0: float = field(default=0.0, init=False, repr=False)
    _t1: float = field(default=0.0, init=False, repr=False)

    def start(self) -> None:
        """Start timing the analysis run."""
        self._t0 = time.perf_counter()

    def stop(self) -> None:
        """Stop timing the analysis run."""
        self._t1 = time.perf_counter()

    @property
    def is_running(self) -> bool:
        return self._t1 == 0.0
    
    @property
    def elapsed(self) -> float:
        if self._t0 == 0:
            return 0.0

        end = time.perf_counter() if self.is_running else self._t1
        return max(0.0, end - self._t0)

    def add_file(self, path: Path, line_count: int) -> None:
        """Record one analyzed file and its line count."""
        self.files_analyzed += 1
        self.lines_analyzed += line_count

    def add_findings(self, items: Iterable[Finding]) -> None:
        """Append multiple findings to the report."""
        self.findings.extend(items)

    def to_text(self) -> str:
        """Render the analysis report as a human-readable text summary."""
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
        """Serialize the analysis report to JSON."""
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
        """Serialize findings to CSV format."""
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
        """Write the report CSV representation to a file."""
        path.write_text(self.to_csv(), encoding="utf-8")


def convert_results(filename: str, results: Iterable[RuleResult]) -> List[Finding]:
    """
    Convert intermediate rule results for a file into full finding objects.
    """
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
    Convert a fixer-like object into a normalized fix dictionary.

    Supports multiple fixer representations by probing common conversion
    methods and attributes such as `to_dict()`, `dsl`, and `to_json()`.
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


def plan_to_fix_dict(fixer: Any, fix_id: str) -> Dict[str, Any]:
    """Backward-compatible alias for `fixer_to_fix_dict`."""
    return fixer_to_fix_dict(fixer, fix_id=fix_id)


def _relpath(p: Path, project_root: Path | None = None) -> str:
    """Return a stable report path, relative to the project root when possible."""
    return to_project_relative_path(p, project_root=project_root)


def build_scan_json(findings: List[Finding], project_root: Path) -> Dict[str, Any]:
    """
    Build normalized scan report JSON from collected findings.

    Assigns stable report-local finding and fix identifiers and converts
    associated fix builders into their serialized report representation.
    """
    project_root = Path(project_root).resolve()
    out: Dict[str, Any] = {"project_root": str(project_root), "findings": []}

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
                "file": _relpath(f.file, project_root=project_root),
                "start_line": start_line,
                "end_line": end_line,
                "message": f.message or "",
                "anchor": asdict(f.anchor) if f.anchor else None,
                "fixes": fixes,
            }
        )
    return out
