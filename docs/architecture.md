# Architecture

[Back to README](../README.md) | [Previous: Fixes](fixes.md) | [Next: Report UI](report-ui.md)

## Workflow

AstAnalyzer supports a full workflow from analysis to controlled code modification:

```text
scan -> select -> patch -> validate -> apply/archive
```

The workflow deliberately separates detection from modification.

## Scan the project

```bash
astanalyzer scan .
```

This generates:

- `scan_report.json`
- `report.html`

Each fix proposal can include a precomputed patch preview, allowing users to inspect changes before generating patch files or modifying source code.

The scan output includes metadata such as:

- severity
- rule identifier
- source location
- code snippet context
- snippet truncation information
- project root

## Select fixes

Open `report.html`, inspect findings, select desired fixes, and export the selected JSON plan.

The generated HTML report is standalone and has no backend dependency.

## Generate patches

```bash
astanalyzer patch
```

or:

```bash
astanalyzer patch --selected path/to/selected.json
```

This step:

- reads selected fixes
- builds patch files
- does not modify source code yet
- validates generated patches with `git apply --check`

## Apply patches

```bash
astanalyzer apply
```

If all checks pass:

- patches are applied to files
- source files are modified
- artifacts and patches are archived

## Archive run

Artifacts can be archived:

- automatically after a successful apply
- manually without applying patches

```bash
astanalyzer archive
```

## Internals

The current implementation uses an import-based plugin model:

- rules are discovered through module import side effects
- built-in rules are loaded first
- custom rule files can be imported dynamically
- rule classes are registered automatically

## Patch creation

- Fix DSL is transformed into a `FixProposal`.
- `FixProposal.get_diff()` generates a unified diff.
- Patch files are written to disk.
- Patches are validated before application.

## Design goals

- safe: no direct mutation during scan
- reviewable: diff-based workflow
- CI-friendly: patch files are portable
- reversible: git handles rollback
- robust: handles paths and artifacts outside project root

## Common pitfalls

- patches may fail if files changed after scan
- missing newline at EOF can break patch application
- older versions may fail on mismatched relative paths
- patches require a git repository, which is strongly recommended

---

[Back to README](../README.md) | [Previous: Fixes](fixes.md) | [Next: Report UI](report-ui.md)
