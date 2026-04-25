# CLI

[Back to README](../README.md) | [Previous: Getting Started](getting-started.md) | [Next: Rules](rules.md)

## Basic usage

By default, the tool scans the project with all loaded rules and focuses on warnings and errors in its output:

```bash
astanalyzer scan ./project
```

## Logging modes

### Info mode

```bash
astanalyzer -v scan ./project
```

### Debug mode

```bash
astanalyzer -vv scan ./project
```

Useful for inspecting:

- matched rules
- general findings
- patch selection flow
- file resolution
- cleanup operations

### Quiet mode

```bash
astanalyzer --quiet scan ./project
```

## Rule selection during scan

AstAnalyzer allows selective execution of rules during the scan phase.

### Run only selected rules

```bash
astanalyzer scan . --only STYLE-010,STYLE-011
```

### Exclude selected rules

```bash
astanalyzer scan . --exclude SEC-003,SEC-006
```

### Run only selected categories

```bash
astanalyzer scan . --only-category STYLE,SEC
```

### Exclude selected categories

```bash
astanalyzer scan . --exclude-category STYLE
```

### Re-include specific rules after exclusion

```bash
astanalyzer scan . --exclude-category STYLE --include STYLE-010
```

### Ignore selected directories

```bash
astanalyzer scan . --exclude-dir tests,venv,migrations
```

## Filter order

Rule filters are applied in the following order:

1. `--only`
2. `--only-category`
3. `--exclude`
4. `--exclude-category`
5. `--include`

This means that `--include` can restore rules that were previously excluded.

## Clean workspace

```bash
astanalyzer clean
```

Optionally:

```bash
astanalyzer clean --include-archive
```

This removes generated artifacts such as:

- selected JSON files
- scan reports
- HTML reports
- patch files
- `used_patches/` when `--include-archive` is used

---

[Back to README](../README.md) | [Previous: Getting Started](getting-started.md) | [Next: Rules](rules.md)
