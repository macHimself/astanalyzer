# AstAnalyzer

AST-based static analysis engine for Python with a declarative DSL for rules and automated fixes.

## What is AstAnalyzer?

AstAnalyzer is a static analysis engine for Python that operates on the abstract syntax tree (AST). It provides a declarative DSL for defining detection rules and safe fix proposals.

Instead of modifying code directly during analysis, AstAnalyzer generates findings and reviewable fix proposals. Selected fixes can then be exported, converted into patches, validated, and applied.

The workflow separates analysis, selection, patch generation, validation, archiving, and application into distinct stages.

## Why this matters

Most static analysis tools report issues and leave the user to inspect files manually. AstAnalyzer adds a review step between detection and modification.

Each fix proposal can include a patch preview, so the user can inspect the exact change before applying it.

This makes automated refactoring safer, more transparent, and easier to control.

## Quick start

```bash
git clone https://github.com/macHimself/astanalyzer.git
cd astanalyzer

python3 -m venv .venv
source .venv/bin/activate

pip install -e '.[dev]'
astanalyzer scan .
```

## Basic workflow

```bash
astanalyzer scan .
```

Generates:

- `scan_report.json`
- `report.html`

Then select fixes in the HTML report and export the selected JSON.

```bash
astanalyzer patch --selected path/to/astanalyzer-selected.json
astanalyzer apply
```

To clean generated artifacts:

```bash
astanalyzer clean
```

## Documentation

Full documentation is available in the [`docs/`](docs/) directory.

| Topic | Description |
|---|---|
| [Getting Started](docs/getting-started.md) | Installation, development setup and first scan |
| [CLI](docs/cli.md) | Command-line usage, logging and rule filters |
| [Architecture](docs/architecture.md) | Scan, review, patch and apply workflow |
| [Report UI](docs/report-ui.md) | Interactive HTML report and fix selection |
| [Patch System](docs/patch-system.md) | Patch generation, validation, application and archiving |
| [Path Resolution](docs/path-resolution.md) | Robust handling of project roots and external artifacts |
| [Rules](docs/rules.md) | Built-in rules, rule IDs, matcher DSL and custom rules |
| [Fixes](docs/fixes.md) | Fixer DSL, fix proposals and refactor helpers |
| [Custom Rules](docs/custom-rules.md) | Extending the analyzer |
| [Ignoring Findings](docs/ignoring-findings.md) | Suppressing rules inline |
| [Examples](docs/examples/basic-rule.md) | Example custom rules |
| [Limitations](docs/limitations.md) | Known constraints |