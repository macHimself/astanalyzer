"""
Naming conversion utilities used by project-wide refactors.
"""

from __future__ import annotations

import re


def to_snake_case(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower()


def to_pascal_case(name: str) -> str:
    if not name:
        return name

    parts = re.split(r"[_\s\-]+", name)
    if len(parts) > 1:
        return "".join(p[:1].upper() + p[1:].lower() for p in parts if p)

    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    parts = s1.split()
    return "".join(p[:1].upper() + p[1:] for p in parts if p)


def to_upper_snake_case(name: str) -> str:
    if not name:
        return name

    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    s3 = re.sub(r"[\s\-]+", "_", s2)
    return s3.upper()