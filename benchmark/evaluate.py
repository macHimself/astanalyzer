import json
import sys
from collections import Counter

if len(sys.argv) != 3:
    print("Usage: python evaluate.py before.json after.json")
    sys.exit(1)


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def stats(report):
    findings = report.get("findings", [])

    return {
        "total": len(findings),
        "by_rule": Counter(f["rule_id"] for f in findings),
        "by_severity": Counter(f["severity"] for f in findings),
        "by_category": Counter(f.get("category", "unknown") for f in findings),
    }


before = stats(load(sys.argv[1]))
after = stats(load(sys.argv[2]))

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