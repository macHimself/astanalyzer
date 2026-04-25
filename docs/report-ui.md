[Back to README](../README.md) | [Previous: Architecture](architecture.md) | [Next: Patch System](patch-system.md)

# Report UI

## Overview

The HTML report is a standalone interactive page generated from the analysis output.

It allows users to inspect findings, review fix proposals, select fixes, and export a JSON plan for patch generation.

## Navigation modes

The report supports two switchable navigation modes:

- **Rule first:** Category -> Rule -> File -> Findings
- **File first:** File -> Category -> Rule -> Findings

The rule-first view is useful when reviewing one type of issue across the project.

The file-first view is useful when fixing several issues inside the same source file.

Both views use the same scan data and preserve selected fixes when switching between modes.

## Hierarchical grouping

In rule-first mode, the report is organized as:

- category
- rule
- file
- individual findings

In file-first mode, the report is organized as:

- file
- category
- rule
- individual findings

Each group displays:

- total number of findings
- severity distribution
- visual severity indicators

## Finding cards

Finding cards are intentionally minimal.

They display:

- finding identifier
- file path and line range
- expandable details

Severity, category, and rule information are not repeated inside every finding card because they are already represented by the surrounding hierarchy.

## Rule-level details

Each rule provides:

- rule identifier
- rule title
- aggregated statistics
- collapsible rule description

Rule descriptions are displayed at the rule level rather than repeated for each finding.

## Guided navigation

The interface supports:

- switchable rule-first and file-first views
- expandable categories, rules, files, and findings
- full-text filtering
- progressive disclosure of details

This reduces cognitive load when working with large reports.

## Severity awareness

Findings are visually distinguished by severity:

- `info` – low importance, informational suggestions
- `warning` – actionable issues
- `error` – critical problems requiring immediate attention

Severity is reflected in:

- aggregated counts per group
- color-coded summary text
- visual highlighting

## Code snippet preview

The report includes contextual code preview.

It:

- shows surrounding lines around the issue
- highlights affected lines
- uses syntax highlighting
- indicates truncated snippets through metadata

Truncation is represented explicitly in the UI, not embedded directly into code snippets.

## Fix proposals

Each fix is presented with:

- short title
- optional reason
- human-readable action description
- patch preview
- expandable raw DSL detail

## Patch preview

Each fix proposal can include a precomputed unified diff.

This allows users to:

- inspect exact code changes before selecting a fix
- understand modification scope without opening source files
- compare multiple fix proposals quickly

The preview highlights:

- added lines
- removed lines
- diff metadata
- context lines

If a preview cannot be generated, the UI displays a fallback message.

## Additional actions

Each finding can support suppression:

- **Suppress this warning**
  - inserts an ignore directive into the source code
  - allows selective suppression directly from the UI

## Export

The report exports selected fixes into a JSON plan.

That JSON is then used by the patch generation step.

---

[Back to README](../README.md) | [Previous: Architecture](architecture.md) | [Next: Patch System](patch-system.md)
