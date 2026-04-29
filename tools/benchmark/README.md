# Benchmark

This directory contains scripts for evaluating the impact of rule precision improvements.

## Methodology

The benchmark compares two versions of the analyzer:

- BEFORE: baseline version (e.g. tag)
- AFTER: improved version (e.g. branch)

The same target project and commit must be used for both runs.

## Usage

```bash
./tools/benchmark/runner.sh /path/to/project before-rules-merge fix/rule-precision-improvements
```

Example:

```bash
./tools/benchmark/runner.sh ~/projects/test-project v0.0.9 v0.1.0
```

## Output

Results are stored in:

```
benchmark/results/<timestamp>/
```

Each run contains:

- `before.json` — findings before changes
- `after.json` — findings after changes
- `summary.txt` — aggregated comparison
- `timing.txt` — execution times
- `meta.json` — run metadata
- `analyzer_commit.txt` — analyzer version
- `project_commit.txt` — analyzed project version

## Notes

- Results are not committed to the repository.
- Each run is immutable and timestamped.
- The goal is to measure reduction of noise and improvement in usability, not formal precision.