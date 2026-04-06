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
    """
    Reference to a named value captured during matcher evaluation.

    References are used in matcher DSL expressions to compare values
    across different parts of the AST, enabling conditions such as
    "same variable" or "matches previously captured value".
    """
    name: str


def ref(name: str) -> Ref:
    """
    Create a reference to a captured value for use in matcher DSL expressions.

    References allow matchers to compare values across different nodes,
    enabling rules such as "uses the same variable" or "matches previously
    captured value".

    Args:
        name (str): Name of the reference.

    Returns:
        Ref: Reference object used in matcher conditions.
    """
    return Ref(name)


@dataclass
class MatchResult:
    """
    Result of a successful matcher evaluation.

    Contains the matched AST node along with all captured references
    collected during the matching process.

    Attributes:
        node (Any): The AST node that satisfied the matcher.
        refs (dict[str, Any]): Mapping of reference names to captured values.
    """
    node: Any
    refs: dict[str, Any]
