"""
Stable anchor utilities for rule findings.

Anchors provide a compact way to identify a specific match across reporting
and later patch-generation steps. They combine source location, symbol path,
and lightweight hashes derived from the matched node and its context.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class FindingAnchor:
    """Stable identifier and metadata for a matched AST node."""

    anchor_id: str
    file: str
    rule_id: str
    node_type: str
    symbol_path: str
    line: Optional[int]
    col: Optional[int]
    end_line: Optional[int]
    end_col: Optional[int]
    source_hash: str
    context_hash: str


def sha256_text(text: str) -> str:
    """Return SHA-256 hex digest for the given text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_source(text: str) -> str:
    """Normalize source text for stable hashing."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines = [line.rstrip() for line in lines]

    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def get_symbol_path(node: Any) -> str:
    """Build dotted symbol path from enclosing classes/functions."""
    parts: list[str] = []
    cur = node

    while cur is not None:
        node_type = cur.__class__.__name__
        name = getattr(cur, "name", None)

        if name and node_type in {"FunctionDef", "AsyncFunctionDef", "ClassDef"}:
            parts.append(name)

        cur = getattr(cur, "parent", None)

    return ".".join(reversed(parts))


def get_node_source(node: Any) -> str:
    """Return best-effort source text for a node."""
    try:
        if hasattr(node, "as_string"):
            return node.as_string()
    except Exception:
        pass
    return ""


def get_source_hash(node: Any) -> str:
    """Return normalized source hash for a node."""
    return sha256_text(normalize_source(get_node_source(node)))


def get_context_hash(node: Any) -> str:
    """Return a lightweight hash describing node location and parent context."""
    parent = getattr(node, "parent", None)
    parent_type = parent.__class__.__name__ if parent else ""
    parent_name = getattr(parent, "name", "") if parent else ""

    payload = "|".join(
        [
            node.__class__.__name__,
            str(getattr(node, "lineno", -1)),
            str(getattr(node, "col_offset", -1)),
            str(getattr(node, "end_lineno", -1)),
            str(getattr(node, "end_col_offset", -1)),
            parent_type,
            str(parent_name),
        ]
    )
    return sha256_text(payload)


def build_anchor(*, rule_id: str, file_path: str, match: Any) -> FindingAnchor:
    """Build a finding anchor for a matched AST node."""
    node_type = match.__class__.__name__
    symbol_path = get_symbol_path(match)
    source_hash = get_source_hash(match)
    context_hash = get_context_hash(match)

    raw_anchor = "|".join(
        [
            rule_id,
            file_path,
            node_type,
            symbol_path,
            str(getattr(match, "lineno", -1)),
            str(getattr(match, "col_offset", -1)),
            str(getattr(match, "end_lineno", -1)),
            str(getattr(match, "end_col_offset", -1)),
            source_hash,
            context_hash,
        ]
    )

    return FindingAnchor(
        anchor_id=sha256_text(raw_anchor),
        file=file_path,
        rule_id=rule_id,
        node_type=node_type,
        symbol_path=symbol_path,
        line=getattr(match, "lineno", None),
        col=getattr(match, "col_offset", None),
        end_line=getattr(match, "end_lineno", getattr(match, "lineno", None)),
        end_col=getattr(match, "end_col_offset", None),
        source_hash=source_hash,
        context_hash=context_hash,
    )