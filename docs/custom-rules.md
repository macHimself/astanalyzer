[Back to README](../README.md) | [Previous: Fixer Actions](fixer-actions.md) | [Next: Ignoring Findings](ignoring-findings.md)

# Custom Rules

AstAnalyzer can be extended with custom rules defined in user-provided Python files or directories.

Custom rules are standard subclasses of `Rule`. Once imported, they are automatically registered and executed alongside built-in rules.

---

## Writing rules

Rules are defined as Python classes that inherit from `Rule`.

A rule typically contains:

- metadata (`id`, `title`, `severity`, `category`, `node_type`)
- one or more `matchers` describing detection logic
- optional `fixer_builders` describing suggested fixes
- optional refactor builders for project-wide transformations

---

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
            fix()
            .comment_before("Custom rule triggered")
            .because("Example custom rule")
        ]
```

---

## Loading custom rules

### Load from a single file

```bash
astanalyzer scan . --rules ./my_rules.py
```

### Load from a directory

```bash
astanalyzer scan . --rules ./my_rules
```

All `.py` files in the directory are imported recursively.

### Load multiple sources

```bash
astanalyzer scan . --rules ./team_rules --rules ./personal_rules.py
```

---

## How it works

- Built-in rules are loaded first
- Custom rule files are imported dynamically
- Importing a module registers rule classes via the `Rule` metaclass
- The scan runs with both built-in and custom rules
- Custom rules can be filtered using standard CLI options

---

## Notes

- Only `.py` files are imported
- Files starting with `_` are skipped
- Custom rules must subclass `Rule`
- Rules are registered at import time (no manual registration needed)
- Prefer declarative matcher chains over custom logic
- Keep rules focused and single-purpose
- Always provide a clear explanation using `.because(...)`

---

## Working with matchers

Custom rules use the same matcher DSL as built-in rules.

You can use:

### Custom predicates

```python
def is_large_function(node):
    return len(node.body) > 10

match("FunctionDef").satisfies(is_large_function)
```

### DSL helper methods

```python
match("FunctionDef").missing_docstring()
match("Assign").is_unused()
match("FunctionDef").multiple_returns()
match("If").redundant_else_after_terminal()
```

For full matcher documentation, see:

[Rules](rules.md)

---

[Back to README](../README.md) | [Previous: Fixer Actions](fixer-actions.md) | [Next: Ignoring Findings](ignoring-findings.md)