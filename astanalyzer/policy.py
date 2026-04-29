"""Policy profiles for scan-time severity handling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .enums import RuleCategory, Severity
from .engine.reporting import Finding


@dataclass(frozen=True)
class PolicyProfile:
    name: str
    severity_overrides: dict[str, str]


POLICIES: dict[str, PolicyProfile] = {
    "default": PolicyProfile(
        name="default",
        severity_overrides={},
    ),
    "ci": PolicyProfile(
        name="ci",
        severity_overrides={
            RuleCategory.SECURITY.value: Severity.ERROR.value,
        },
    ),
    "strict": PolicyProfile(
        name="strict",
        severity_overrides={
            RuleCategory.SECURITY.value: Severity.ERROR.value,
            RuleCategory.SEMANTIC.value: Severity.ERROR.value,
            RuleCategory.RESOURCE.value: Severity.ERROR.value,
        },
    ),
}


def get_policy(name: str | None) -> PolicyProfile:
    policy_name = name or "default"

    try:
        return POLICIES[policy_name]
    except KeyError as exc:
        known = ", ".join(sorted(POLICIES))
        raise ValueError(f"Unknown policy '{policy_name}'. Available policies: {known}") from exc


def apply_policy_to_finding(finding: Finding, policy: PolicyProfile) -> Finding:
    override = policy.severity_overrides.get(str(finding.category))

    if override:
        finding.severity = override

    return finding


def apply_policy(findings: Iterable[Finding], policy: PolicyProfile) -> list[Finding]:
    return [apply_policy_to_finding(finding, policy) for finding in findings]
