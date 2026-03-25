"""
Small data structures used by the matcher DSL.

This module contains lightweight value objects representing:
- named references used in matcher comparisons
- structured match results with captured context
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Ref:
    """Reference to a named value captured during matching."""
    name: str


def ref(name: str) -> Ref:
    return Ref(name)


@dataclass
class MatchResult:
    """Successful matcher result including the matched node and captured refs."""
    node: Any
    refs: dict[str, Any]