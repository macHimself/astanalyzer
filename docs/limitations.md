[Back to README](../README.md) | [Previous: Ignoring Findings](ignoring-findings.md)

# Limitations

AstAnalyzer is designed for practical static analysis and controlled refactoring. Some limitations are intentional.

## Matcher limitations

- Matchers are lightweight and best-effort
- They do not implement full semantic analysis
- Complex patterns may require custom predicates

## Fixer limitations

- Fixers are primarily line-based, not full AST transformations
- Some actions affect only the matched node
- Some actions switch to full-file mode (e.g. imports)
- Fix suggestions may still require human review

## Refactor limitations

- Refactors are approximate and text-based
- They are not backed by a full symbol table
- They should always be reviewed before applying

## Patch limitations

- Patches may fail if source files change after scan
- Missing newline at EOF can break patch application (handled internally when possible)
- Git repository is strongly recommended for patch application

## General limitations

- Some rules provide suggestions rather than fully automated fixes
- Complex transformations may require custom fixers or multiple passes

---

[Back to README](../README.md) | [Previous: Ignoring Findings](ignoring-findings.md)
