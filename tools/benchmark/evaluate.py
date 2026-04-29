import os
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
from collections import Counter, defaultdict

CATEGORY_BY_PREFIX = {
    "STYLE": "style",
    "DEAD": "dead_code",
    "SEM": "semantic",
    "CX": "complexity",
    "PERF": "performance",
    "SEC": "security",
    "RES": "resource",
}


if len(sys.argv) not in (3, 5):
    print("Usage: python evaluate.py before.json after.json [coverage_before.json coverage_after.json]")
    sys.exit(1)


def extract_coverage_by_module(coverage_json):
    files = coverage_json.get("files", {})
    modules = defaultdict(list)

    for path, data in files.items():
        parts = path.split("/")
        module = parts[1] if len(parts) >= 2 else "root"

        percent = data.get("summary", {}).get("percent_covered", 0)
        modules[module].append(percent)

    return {
        module: round(sum(values) / len(values), 2)
        for module, values in sorted(modules.items())
    }


def coverage_stats(path):
    data = load(path)
    totals = data.get("totals", {})

    return {
        "covered_lines": totals.get("covered_lines"),
        "num_statements": totals.get("num_statements"),
        "missing_lines": totals.get("missing_lines"),
        "excluded_lines": totals.get("excluded_lines"),
        "percent_covered": totals.get("percent_covered"),
        "by_module": extract_coverage_by_module(data),
    }


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def category_from_rule_id(rule_id):
    prefix = rule_id.split("-", 1)[0]
    return CATEGORY_BY_PREFIX.get(prefix, "unknown")


def stats(report):
    findings = report.get("findings", [])

    return {
        "total": len(findings),
        "by_rule": Counter(f["rule_id"] for f in findings),
        "by_severity": Counter(f["severity"] for f in findings),
        "by_category": Counter(
            category_from_rule_id(f["rule_id"]) for f in findings
        ),
    }


def counter_to_dict(value):
    return dict(value)


def build_structured_result(before, after, coverage_before=None, coverage_after=None):
    all_rules = set(before["by_rule"]) | set(after["by_rule"])
    all_categories = set(before["by_category"]) | set(after["by_category"])
    all_severities = set(before["by_severity"]) | set(after["by_severity"])

    return {
        "project": {
            "name": os.getenv("AST_PROJECT_NAME"),
            "path": os.getenv("AST_PROJECT_PATH"),
        },
        "before_ref": os.getenv("AST_BASE_REF"),
        "after_ref": os.getenv("AST_TEST_REF"),
        "timestamp": os.getenv("AST_TIMESTAMP")
        or datetime.now(timezone.utc).isoformat(),
        "results": {
            "before": {
                "total": before["total"],
                "by_rule": counter_to_dict(before["by_rule"]),
                "by_severity": counter_to_dict(before["by_severity"]),
                "by_category": counter_to_dict(before["by_category"]),
            },
            "after": {
                "total": after["total"],
                "by_rule": counter_to_dict(after["by_rule"]),
                "by_severity": counter_to_dict(after["by_severity"]),
                "by_category": counter_to_dict(after["by_category"]),
            },
            "diff": {
                "total": after["total"] - before["total"],
                "by_rule": {
                    rule: after["by_rule"].get(rule, 0) - before["by_rule"].get(rule, 0)
                    for rule in sorted(all_rules)
                },
                "by_severity": {
                    severity: after["by_severity"].get(severity, 0) - before["by_severity"].get(severity, 0)
                    for severity in sorted(all_severities)
                },
                "by_category": {
                    category: after["by_category"].get(category, 0) - before["by_category"].get(category, 0)
                    for category in sorted(all_categories)
                },
            },
        },
        "astanalyzer_test_coverage": {
            "before": coverage_before,
            "after": coverage_after,
            "diff": (
                None
                if coverage_before is None or coverage_after is None
                else {
                    "percent_covered": coverage_after["percent_covered"] - coverage_before["percent_covered"],
                    "covered_lines": coverage_after["covered_lines"] - coverage_before["covered_lines"],
                    "num_statements": coverage_after["num_statements"] - coverage_before["num_statements"],
                    "missing_lines": coverage_after["missing_lines"] - coverage_before["missing_lines"],
                }
            ),
        },
    }


def write_structured_result(result):
    output_dir = Path(os.getenv("AST_OUTPUT_DIR", "."))
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "benchmark_result.json"

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)


before = stats(load(sys.argv[1]))
after = stats(load(sys.argv[2]))

coverage_before = None
coverage_after = None

if len(sys.argv) == 5:
    coverage_before = coverage_stats(sys.argv[3])
    coverage_after = coverage_stats(sys.argv[4])

print("=== TOTAL ===")
print(f"Before: {before['total']}")
print(f"After:  {after['total']}")
print(f"Change: {after['total'] - before['total']}")
print()

print("=== BY SEVERITY ===")
print("Before:", dict(before["by_severity"]))
print("After: ", dict(after["by_severity"]))
print()

print("=== BY CATEGORY ===")
print("Before:", dict(before["by_category"]))
print("After: ", dict(after["by_category"]))
print()

print("=== TOP RULE CHANGES ===")

all_rules = set(before["by_rule"]) | set(after["by_rule"])

for rule in sorted(all_rules):
    b = before["by_rule"].get(rule, 0)
    a = after["by_rule"].get(rule, 0)
    if b != a:
        print(f"{rule}: {b} -> {a} ({a - b:+})")

write_structured_result(
    build_structured_result(before, after, coverage_before, coverage_after)
)