# astanalyzer

AST-based static analysis engine with DSL for Python.

## Setup (development)

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

# Run tests

```bash
pytest
```

## Install

```bash
pip install -e .
```

## Usage
astanalyzer scan ./project