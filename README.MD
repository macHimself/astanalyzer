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

## Run tests

```bash
pytest
```

## Install

```bash
pip install -e .
```

## Usage
run without any verbosity flag, the tool shows only warnings and errors: 
```bash
astanalyzer scan ./project
```

### Running without installed CLI entrypoint
If you are running the module directly, the same flasgs works: 
```bash
python -m astanalyzer.cli -vv scan .
```

### Info mode
Use -v to enable informational logs:
```bash
astanalyzer -v scan ./project
```

### Debug mode
Use -vv to enable debug logging:
```bash
astanalyzer -vv scan ./project
```
this option is useful when you want to inspect 
matched rules
general fidings
patch selection flow
file resolution
cleanup operations

### Quiet mode
Use --quiet to show only errors:
```bash
astanalyzer --quiet scan ./project
```

## Working with patches

### Patch workflow

AstAnalyzer supports a full workflow from analysis to automated code modification.
#### Scan the project 
```bash
astanalyzer scan .
```
This generates: 
scan_report.json
report.html (interactive UI for selecting fixes)

Select fixes in the browser
Open report.html, select desired fixes, and export:

#### Generate patches
```bash
astanalyzer patch
```
or explicitly:

```bash
astanalyzer patch path/to/selected.json
```
This step:
reads selected fixes
builds patch files (*.patch)
does NOT modify source code yet


#### Validate patches (dry-run)
Validation is automatically executed during patching, but can also be done manually:
```bash
astanalyzer apply --check
```
This ensures:
patch is syntactically valid
patch can be applied cleanly
no conflicts exist

#### Apply patches
```bash
astanalyzer apply
```
If all checks pass: 
patches are applied to files
files are modified

#### Archive run
After successful apply:
selected JSON 
scan report
HTML report
patch files

are moved to: 
```bash
used_runs/<timestamp>/
```

#### Clean workspace
```bash
astanalyzer clean
```
optional:
```bash
astanalyzer clean --include-archive
```
This removes:
selected JSON 
scan report
HTML report
patch files
and used_runs/

## What actually happens under the hood

#### Patch creation:

Fix DSL -> transformed into FixProposal
FixProposal.get_diff() generates unified diff
Patch files are written to disk 

#### Patch validation:
Each patch is checked using:
```bash
git apply --check
```
This verifies:
correct diff format
correct context lines
file consistency


#### Patch application
Patches are applied using
```bash
git apply
```
This modifies files directly.

## Why this design?

safe (no direct mutation during scan)
reviewable (diff-based workflow)
CI-friendly (patch files are portable)
revisible (git handles rollback)

### Common pitfalls
patches fail if file changed after scan 
missing newline at EOF can break the patch -> auto-fixed
relative patch must match project structure
patches require a git repository (recomended)

