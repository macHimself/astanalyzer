[Back to README](../README.md) | [Previous: Getting Started](getting-started.md) | [Next: Architecture](architecture.md)

# CLI

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

## Scan policy

AstAnalyzer supports policy profiles that control how findings are evaluated.

Policies do not change which issues are detected. Instead, they define how
severity levels are interpreted in different contexts (e.g. local development vs CI).

### Usage

```bash
astanalyzer scan . --policy default
astanalyzer scan . --policy ci
astanalyzer scan . --policy strict
```

### Available policies

#### `default`

Uses rule-defined severity without modification.

#### `ci`

Promotes security findings to errors.

```text
SECURITY: warning → error
```

#### `strict`

Applies stricter enforcement for critical categories.

```text
SECURITY → error
SEMANTIC → error
RESOURCE → error
```

### How it works

The scan pipeline consists of two phases:

```text
rules → findings → policy → report
```

Rules detect issues and assign default severity. The selected policy can
override these values before results are reported.

### Notes

- Policies do not filter findings.
- Use `--exclude` or `--only` for filtering.
- Policies only affect severity and reporting behaviour.

## Patch generation

Generate patch files from the exported selected JSON plan:

```bash
astanalyzer patch
```

If no path is provided, AstAnalyzer attempts to locate the selected JSON file automatically using the following order:

1. `astanalyzer-selected.json` in the current working directory
2. `selected.json` in the current working directory
3. fallback to the current working directory

You can also provide the selected JSON file explicitly:

```bash
astanalyzer patch path/to/astanalyzer-selected.json
```

This command:

- reads selected fixes
- generates `.patch` files
- does not modify source files
- validates generated patches using `git apply --check`

## Patch validation

Validate generated patches without applying them:

```bash
astanalyzer apply --check
```

This checks whether patches can be applied cleanly.

## Apply patches

Apply generated patches:

```bash
astanalyzer apply
```

If all checks pass, source files are modified and generated artifacts are archived.

## Archive artifacts

Archive generated artifacts without applying patches:

```bash
astanalyzer archive
```

or with explicit selected JSON:

```bash
astanalyzer archive path/to/astanalyzer-selected.json
```

This moves generated artifacts into:

```text
used_patches/<timestamp>/
```

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

[Back to README](../README.md) | [Previous: Getting Started](getting-started.md) | [Next: Architecture](architecture.md)
