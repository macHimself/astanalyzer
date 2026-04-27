[Back to README](../README.md) | [Next: CLI](cli.md)

# Getting Started

## Development setup

Create virtual environment:

```bash
git clone https://github.com/macHimself/astanalyzer.git
cd astanalyzer
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Deactivate virtual environment:

```bash
deactivate
```

## Run tests

```bash
pytest
```

## Install

```bash
pip install -e .
```

## First scan

```bash
astanalyzer scan .
```

This generates:

- `scan_report.json`
- `report.html`

Open the generated HTML report, review findings, select fixes, and export the selected JSON plan.

## Running without installed CLI entrypoint

```bash
python -m astanalyzer.cli -vv scan .
```

---

[Back to README](../README.md) | [Next: CLI](cli.md)
