"""
Helpers for inline and block-based rule suppression.

Supported comment forms:

    astanalyzer: ignore RULE-001, RULE-002
    astanalyzer: ignore-next RULE-001
    astanalyzer: disable RULE-001
    astanalyzer: enable RULE-001

Wildcard suppression is supported via:

    astanalyzer: ignore
    astanalyzer: ignore-next
    astanalyzer: disable
    astanalyzer: enable
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

IGNORE_PREFIX = "astanalyzer:"


def _parse_ignore_rule_ids(text: str) -> set[str]:
    """Parse inline ignore directives and return rule IDs or wildcard."""
    if not text:
        return set()

    text = text.strip()
    if IGNORE_PREFIX not in text:
        return set()

    try:
        _, rest = text.split(IGNORE_PREFIX, 1)
    except ValueError:
        return set()

    rest = rest.strip()

    if rest.startswith("ignore-next"):
        rest = rest[len("ignore-next") :].strip()
    elif rest.startswith("ignore"):
        rest = rest[len("ignore") :].strip()
    else:
        return set()

    if not rest:
        return {"*"}

    parts = [p.strip() for p in rest.split(",")]
    return {p for p in parts if p}


def _parse_toggle_command(text: str) -> tuple[str | None, set[str]]:
    """Parse block enable/disable directives.

    Returns:
        ("disable", {"COND-002"})
        ("enable", {"COND-002"})
        ("disable", {"*"})
        ("enable", {"*"})
        (None, set())
    """
    if not text:
        return None, set()

    text = text.strip()
    if IGNORE_PREFIX not in text:
        return None, set()

    try:
        _, rest = text.split(IGNORE_PREFIX, 1)
    except ValueError:
        return None, set()

    rest = rest.strip()

    if rest.startswith("disable"):
        cmd = "disable"
        rest = rest[len("disable") :].strip()
    elif rest.startswith("enable"):
        cmd = "enable"
        rest = rest[len("enable") :].strip()
    else:
        return None, set()

    if not rest:
        return cmd, {"*"}

    parts = [p.strip() for p in rest.split(",")]
    return cmd, {p for p in parts if p}


def _is_disabled_by_block(rule_id: str, lines: list[str], lineno: int) -> bool:
    """Check whether a rule is disabled by earlier block directives."""
    disabled_all = False
    disabled_rules: set[str] = set()

    for i in range(min(lineno - 1, len(lines))):
        line = lines[i].strip()
        cmd, ids = _parse_toggle_command(line)

        if cmd is None:
            continue

        if cmd == "disable":
            if "*" in ids:
                disabled_all = True
            else:
                disabled_rules.update(ids)

        elif cmd == "enable":
            if "*" in ids:
                disabled_all = False
                disabled_rules.clear()
            else:
                disabled_rules.difference_update(ids)

    return disabled_all or rule_id in disabled_rules


def is_ignored_for_node(rule_id: str, node: Any) -> bool:
    """Return True if the given rule should be ignored for this node."""
    root = node.root()
    lines = getattr(root, "file_by_lines", None)
    if not lines:
        return False

    lineno = getattr(node, "lineno", None)
    if lineno is None or lineno < 1:
        return False

    current_line = lines[lineno - 1] if lineno - 1 < len(lines) else ""
    prev_line = lines[lineno - 2] if lineno - 2 >= 0 else ""

    if _is_disabled_by_block(rule_id, lines, lineno):
        log.debug("[IGNORE BLOCK] rule=%s line=%s", rule_id, lineno)
        return True

    ids = _parse_ignore_rule_ids(current_line)
    if "*" in ids or rule_id in ids:
        log.debug(
            "[IGNORE INLINE] rule=%s line=%s ids=%s code=%r",
            rule_id,
            lineno,
            ids,
            current_line.strip(),
        )
        return True

    prev = prev_line.strip()
    prev_ids = _parse_ignore_rule_ids(prev)

    if IGNORE_PREFIX in prev and "ignore-next" in prev:
        if "*" in prev_ids or rule_id in prev_ids:
            log.debug(
                "[IGNORE NEXT] rule=%s line=%s ids=%s trigger_line=%r",
                rule_id,
                lineno,
                prev_ids,
                prev,
            )
            return True

    return False
