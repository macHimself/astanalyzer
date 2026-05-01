[Back to README](../README.md) | [Next: Getting Started](getting-started.md)

## Example Report

This section demonstrates how AstAnalyzer presents analysis results across both CLI and the interactive HTML report.

---

### CLI Scan Summary

The command-line interface provides a high-level summary of the analysis, including file count, total findings, category distribution, and performance metrics.

![CLI scan summary](img/4-cli.png)

---

### Report Overview

The HTML report provides an interactive overview of all detected findings, grouped by category and rule. It allows fast navigation and prioritisation.

![Report overview](img/overview.png)

---

### Rule Detail

Rules include structured explanations using the WHAT / WHY / WHEN / HOW / LIMITATIONS model, helping users understand both the issue and its impact.

![Rule detail](img/rule-detail-security.png)

---

### Finding Detail

Each finding includes a contextual code preview, precise location, and structured explanation to support quick understanding and validation.

![Finding detail](img/finding-detail.png)

---

## Patch Workflow (CLI)

### Patch Generation

![CLI patch generation – detection and validation](img/5-cli-patch.png)

*Figure: Patch generation step showing detected patches and validation results.*

---

### Patch Validation (Dry Run)

![CLI apply --check – dry-run validation](img/6-cli-apply-check.png)

*Figure: Dry-run mode verifies that patches can be applied without modifying files.*

---

### Patch Application

![CLI apply – patch application and archiving](img/7-cli-apply.png)

*Figure: Successful patch application followed by archiving of processed files.*

---

### Cleanup

![CLI clean – removal of generated artifacts](img/8-cli-clean.png)

*Figure: Cleanup operation removing generated files and optional archive.*

---

### Result Verification

![Applied fix example – hardcoded secret](img/9-applied-patch.png)

*Figure: Example of an applied fix resolving a detected security issue (hardcoded secret).*

---

[Back to README](../README.md) | [Next: Getting Started](getting-started.md)