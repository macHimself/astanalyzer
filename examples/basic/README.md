# Basic example

This example shows how AstAnalyzer detects common issues
in a small Python file.

## Run analysis

From this directory:

```bash
astanalyzer scan .
```

This will generate:

- `report.html` – interactive report  
- `scan_report.json` – machine-readable output  

## What is detected

The analyzer should report issues such as:

- always true condition  
- mutable default argument  
- comparison to None using `==`  
- debug print statement  
- redundant else block  

## View results

Open the report in your browser:

```bash
open report.html
```

Select fixes in the UI and export them, then run:

```bash
astanalyzer patch
```

---

This example is intentionally small but demonstrates multiple
rule categories at once.