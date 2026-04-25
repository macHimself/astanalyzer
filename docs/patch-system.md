# Patch System

[Back to README](../README.md) | [Previous: Report UI](report-ui.md) | [Next: Path Resolution](path-resolution.md)

## Generate patches

```bash
astanalyzer patch
```

or explicitly:

```bash
astanalyzer patch --selected path/to/selected.json
```

This step:

- reads selected fixes
- builds patch files
- does not modify source code yet
- validates generated patches using `git apply --check`

The selected JSON contains the original `project_root`, which is used to resolve source files and patch locations.

## Validate patches

Validation is automatically executed during patch generation.

It can also be done manually:

```bash
astanalyzer apply --check
```

This ensures that:

- the patch is syntactically valid
- the patch can be applied cleanly
- no conflicts exist

## Apply patches

```bash
astanalyzer apply
```

If all checks pass:

- patches are applied to files
- source files are modified
- generated artifacts are archived

## Archive generated artifacts without applying patches

```bash
astanalyzer archive
```

The archive command can also receive an explicit selected JSON file:

```bash
astanalyzer archive path/to/astanalyzer-selected.json
```

When a selected JSON file is available, AstAnalyzer reads its `project_root` value and uses it to locate generated patch files.

## Selected JSON lookup order

The archive command looks for selected JSON in this order:

1. explicitly provided path
2. `astanalyzer-selected.json` in the current working directory
3. `selected.json` in the current working directory
4. fallback to the current working directory

## Archive structure

Generated artifacts are moved into:

```text
used_patches/<timestamp>/
```

Archived artifacts may include:

- selected JSON
- scan report
- HTML report
- generated patch files

Patch files are stored under:

```text
used_patches/<timestamp>/patches/
```

The original patch directory structure is preserved relative to the detected project root.

## Clean workspace

```bash
astanalyzer clean
```

Optionally:

```bash
astanalyzer clean --include-archive
```

This removes:

- selected JSON
- scan report
- HTML report
- patch files
- `used_patches/` when `--include-archive` is used

---

[Back to README](../README.md) | [Previous: Report UI](report-ui.md) | [Next: Path Resolution](path-resolution.md)
