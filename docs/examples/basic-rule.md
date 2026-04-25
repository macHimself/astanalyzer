# Basic Rule Example

[Back to README](../../README.md) | [Previous: Path Resolution](../path-resolution.md) | [Next: Advanced Matcher](advanced-matcher.md)

## Detect a function named `foo`

This example shows a minimal custom rule.

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
            .because("The function name matches the custom rule condition.")
        ]
```

## Load the rule

```bash
astanalyzer scan . --rules ./my_rules.py
```

## Notes

- Custom rules must subclass `Rule`.
- Rules are registered when imported.
- Prefer declarative matcher chains over custom Python predicates.
- Always provide a clear fix reason with `because(...)`.

---

[Back to README](../../README.md) | [Previous: Path Resolution](../path-resolution.md) | [Next: Advanced Matcher](advanced-matcher.md)
