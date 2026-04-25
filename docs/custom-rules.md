[Back to README](../README.md) |  [Next: Ignoring Findings](ignoring-findings.md) | [Previous: Limitations](limitations.md)

# Custom Rules

AstAnalyzer can load custom rules from user-provided Python files or directories.

Custom rules are normal subclasses of `Rule`. Once imported, they are registered automatically through the rule registry.

## Writing rules

Rules are defined as Python classes that inherit from `Rule`.

A rule usually contains:

- metadata (`id`, `title`, `severity`, `category`, `node_type`)
- one or more `matchers` describing what should be detected
- optional `fixer_builders` describing suggested fixes
- optional refactor builders for project-wide transformations

## Example custom rule

```python
from astanalyzer.enums import Severity, RuleCategory, NodeType
from astanalyzer.fixer import fix
from astanalyzer.matcher import match
from astanalyzer.rule import Rule


class MyCustomRule(Rule):
    id = "CUST-001"
    title = "Detect foo function"
    severity = Severity.INFO
    category = RuleCategory.STYLE
    node_type = NodeType.FUNCTION_DEF

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("FunctionDef").where("name", "foo")
        ]
        self.fixer_builders = [
            fix().comment_before("Custom rule triggered")
        ]
```

## Load custom rules from CLI

### Load from a single file

```bash
astanalyzer scan . --rules ./my_rules.py
```

### Load from a directory

```bash
astanalyzer scan . --rules ./my_rules
```

All `.py` files in the directory recursively will be imported.

### Load multiple rule sources

```bash
astanalyzer scan . --rules ./team_rules --rules ./personal_rules.py
```

## How it works

- Built-in rules are loaded first
- Custom rule files are imported dynamically
- Importing a module registers its rule classes automatically via `Rule` metaclass
- The scan then runs with both built-in and custom rules
- Custom rules can also be targeted by scan filters if they define stable rule IDs

## Notes

- Only `.py` files are imported
- Files starting with `_` are skipped when loading from a directory
- Custom rules must subclass `Rule`
- Rules are registered at import time; no manual registration is needed
- Prefer declarative matcher chains over custom logic
- Keep rules focused and single-purpose
- Always provide a clear explanation (`because(...)`) for fixes

---

[Back to README](../README.md) |  [Next: Ignoring Findings](ignoring-findings.md) | [Previous: Limitations](limitations.md)