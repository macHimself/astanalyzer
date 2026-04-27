"""Console output helpers for the astanalyzer CLI."""

from __future__ import annotations

from typing import Any

def print_section(title: str) -> None:
    """Print a formatted section header for CLI output."""
    print()
    print("=" * 60)
    print(title)

def print_kv(key: str, value: Any) -> None:
    """Print a key–value pair aligned for CLI output."""
    print(f"{key:<20} {value}")
