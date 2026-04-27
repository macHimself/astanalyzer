[Back to README](../README.md) | [Next: Path Resolution](path-resolution.md) | [Next: Rule Catalog](rule-catalog.md)

# Rules

AstAnalyzer includes built-in static analysis rules for Python code.

## Categories

Rules are grouped into six categories:

- `STYLE` (STYLE) – code style, formatting, readability 
- `SEMANTIC` (SEM) – semantic issues 
- `SECURITY` (SEC) – security risks 
- `PERFORMANCE` (PERF) – performance issues 
- `DEAD_CODE` (DEAD)– dead code
- `COMPLEXITY` (CX)– complexity and maintainability problems 

## Rule ID format

Each rule has a stable identifier:

```
<CATEGORY>-<NUMBER>
```

Examples:

- `STYLE-004`
- `SEC-001`
- `CX-003`

Rule IDs are used for:

- identifying findings
- filtering rules in CLI
- grouping issues in reports
- mapping fixes and patches

---

## Documentation

- [Rule Catalog](rule-catalog.md) — full list of built-in rules  
- [Rule DSL](rule-dsl.md) — how rules are defined  
- [Custom Rules](custom-rules.md) — how to extend the analyzer  

---

[Back to README](../README.md) | [Next: Path Resolution](path-resolution.md) | [Next: Rule Catalog](rule-catalog.md)