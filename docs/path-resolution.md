[Back to README](../README.md) | [Previous: Patch System](patch-system.md) | [Next: Rules](rules.md)

# Path Resolution

## Overview

AstAnalyzer does not assume that analysis artifacts are located inside the project root.

Artifacts such as selected JSON files can be stored or processed externally.

## Project root

The selected JSON file stores the original `project_root`.

This value is reused during:

- patch generation
- patch validation
- patch application
- artifact archiving

## Why this matters

Without consistent path resolution, patch generation can fail when:

- `scan_report.json` is outside the project root
- selected JSON is exported to another directory
- commands are executed from a different working directory
- patch files need to be archived after external processing

## Normalization

All paths are normalized and resolved consistently across the pipeline.

This prevents failures caused by mismatched relative and absolute paths.

## Archive support

When archiving artifacts, AstAnalyzer can read the selected JSON file, detect the original project root, and locate generated patch files relative to that root.

This allows archiving to work even when the command is executed outside the scanned project directory.

## Practical result

The workflow remains stable even when intermediate artifacts are moved outside the project.

This improves robustness in practical use cases, especially CI pipelines and manual review workflows.

---

[Back to README](../README.md) | [Previous: Patch System](patch-system.md) | [Next: Rules](rules.md)
