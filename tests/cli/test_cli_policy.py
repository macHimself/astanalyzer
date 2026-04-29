from astanalyzer.engine.reporting import Finding
from astanalyzer.policy import get_policy, apply_policy
from pathlib import Path


def test_default_policy_does_not_change_severity():
    finding = Finding(
        file=Path("x.py"),
        rule_id="SEC-001",
        category="security",
        severity="warning",
    )

    result = apply_policy([finding], get_policy("default"))

    assert result[0].severity == "warning"


def test_ci_policy_promotes_security_to_error():
    finding = Finding(
        file=Path("x.py"),
        rule_id="SEC-001",
        category="security",
        severity="warning",
    )

    result = apply_policy([finding], get_policy("ci"))

    assert result[0].severity == "error"


def test_strict_policy_promotes_semantic_to_error():
    finding = Finding(
        file=Path("x.py"),
        rule_id="SEM-004",
        category="semantic",
        severity="warning",
    )

    result = apply_policy([finding], get_policy("strict"))

    assert result[0].severity == "error"
