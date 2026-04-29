# astanalyzer

AST-based static analysis engine for Python with a declarative DSL for rules and automated fixes.

---

## What is AstAnalyzer?

AstAnalyzer is a static analysis tool that operates on the abstract syntax tree (AST) of Python code.

It allows you to:

- detect issues using a declarative rule DSL
- review findings in an interactive HTML report
- select fixes before applying changes
- generate and validate patch files
- apply changes in a controlled and reproducible way

---

## Why this matters

Most static analysis tools produce reports that require manual inspection.

AstAnalyzer changes the workflow:

```text
scan → review → select → patch → apply
```

This approach:

- improves safety (no automatic changes during scan)
- makes refactoring transparent (patch previews)
- supports CI workflows
- allows controlled code transformations

---

## Quick start

```bash
git clone https://github.com/macHimself/astanalyzer.git
cd astanalyzer

python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

astanalyzer scan .
```

This generates:

- `scan_report.json`
- `report.html` (interactive UI)

Open `report.html`, select fixes, export selection, then:

```bash
astanalyzer patch
astanalyzer apply
```

---

## Core workflow

1. **Scan**
   ```bash
   astanalyzer scan .
   ```

2. **Review**
   - open `report.html`
   - inspect findings
   - select fixes

3. **Generate patches**
   ```bash
   astanalyzer patch
   ```

4. **Apply changes**
   ```bash
   astanalyzer apply
   ```

---

## Documentation

### Getting started

- [Example](docs/example.md) – example output and interactive report walkthrough
- [Getting Started](docs/getting-started.md) — installation and setup  
- [CLI](docs/cli.md) — commands and options  

### Core concepts

- [Architecture](docs/architecture.md) — workflow and design  
- [Report UI](docs/report-ui.md) — interactive report  
- [Patch System](docs/patch-system.md) — patch generation and application  
- [Path Resolution](docs/path-resolution.md) — robust file handling  

### Rules and DSL

- [Rules](docs/rules.md) — categories and rule structure  
- [Rule Catalog](docs/rule-catalog.md) — built-in rules  
- [Rule DSL](docs/rule-dsl.md) — matcher DSL  
- [Matcher Helpers](docs/matcher-helpers.md) — advanced matching helpers  

### Fixes and transformations

- [Fixes](docs/fixes.md) — fixer DSL  
- [Fixer Actions](docs/fixer-actions.md) — available fix operations  

### Extensibility

- [Custom Rules](docs/custom-rules.md) — extending the analyzer  
- [Ignoring Findings](docs/ignoring-findings.md) — suppressing rules  

### Reference

- [Limitations](docs/limitations.md) — known constraints  

---

## Benchmark

AstAnalyzer provides a simple benchmark setup for evaluating the impact of rule changes.

The benchmark compares two versions of the analyzer (e.g. a baseline tag and an improved branch) on the same project and commit.

Run:

```bash
./benchmark/runner.sh /path/to/project before-ref after-ref
```

Example:

```bash
./benchmark/runner.sh ~/projects/test-project before-rules-merge improvements
```

Results are stored in:

```
benchmark/results/<timestamp>/
```

Each run includes:

- before/after findings (`.json`)
- summary comparison
- execution time
- metadata for reproducibility

For more details, see:

[Benchmark documentation](benchmark/README.md)
