#!/usr/bin/env bash

set -e

mkdir -p docs/examples

cat > docs/getting-started.md <<'EOF'
# Getting Started

[Back to README](../README.md) | [Next: CLI](cli.md)

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
EOF

cat > docs/cli.md <<'EOF'
# CLI

[Back to README](../README.md) | [Previous: Getting Started](getting-started.md) | [Next: Rules](rules.md)

## Basic usage

By default, the tool scans the project with all loaded rules and focuses on warnings and errors in its output:

```bash
astanalyzer scan ./project
```

## Logging modes

### Info mode

```bash
astanalyzer -v scan ./project
```

### Debug mode

```bash
astanalyzer -vv scan ./project
```

Useful for inspecting:

- matched rules
- general findings
- patch selection flow
- file resolution
- cleanup operations

### Quiet mode

```bash
astanalyzer --quiet scan ./project
```

## Rule selection during scan

AstAnalyzer allows selective execution of rules during the scan phase.

### Run only selected rules

```bash
astanalyzer scan . --only STYLE-010,STYLE-011
```

### Exclude selected rules

```bash
astanalyzer scan . --exclude SEC-003,SEC-006
```

### Run only selected categories

```bash
astanalyzer scan . --only-category STYLE,SEC
```

### Exclude selected categories

```bash
astanalyzer scan . --exclude-category STYLE
```

### Re-include specific rules after exclusion

```bash
astanalyzer scan . --exclude-category STYLE --include STYLE-010
```

### Ignore selected directories

```bash
astanalyzer scan . --exclude-dir tests,venv,migrations
```

## Filter order

Rule filters are applied in the following order:

1. `--only`
2. `--only-category`
3. `--exclude`
4. `--exclude-category`
5. `--include`

This means that `--include` can restore rules that were previously excluded.

## Clean workspace

```bash
astanalyzer clean
```

Optionally:

```bash
astanalyzer clean --include-archive
```

This removes generated artifacts such as:

- selected JSON files
- scan reports
- HTML reports
- patch files
- `used_patches/` when `--include-archive` is used

---

[Back to README](../README.md) | [Previous: Getting Started](getting-started.md) | [Next: Rules](rules.md)
EOF

cat > docs/rules.md <<'EOF'
# Rules

[Back to README](../README.md) | [Previous: CLI](cli.md) | [Next: Fixes](fixes.md)

## Built-in Rules

AstAnalyzer includes built-in static analysis rules for Python code.

The rules are grouped into six categories:

- `STYLE` – code style, formatting, readability, naming and documentation
- `SEM` – semantic issues and suspicious or misleading logic
- `SEC` – security-related patterns and risks
- `PERF` – performance and efficiency issues
- `DEAD` – dead code and unreachable logic
- `CX` – complexity and maintainability problems

## Rule ID format

Each rule is identified by a stable ID:

```text
<CATEGORY>-<NUMBER>
```

Examples:

- `STYLE-004`
- `SEC-001`
- `CX-003`

Rule IDs are used for:

- identifying findings in reports
- filtering and grouping issues
- selecting rules from CLI
- referencing rules in CI pipelines
- mapping fixes and patches to specific rules

## STYLE rules

### STYLE-001 – EmptyBlock

**Severity:** warning

```python
if ready:
    pass
```

### STYLE-002 – RedundantIfElseReturn

**Severity:** info

```python
def is_valid(x):
    if x > 0:
        return True
    else:
        return False
```

### STYLE-003 – MultipleReturnsInFunction

**Severity:** info

```python
def classify(x):
    if x < 0:
        return "neg"
    if x == 0:
        return "zero"
    return "pos"
```

### STYLE-004 – LineTooLong

**Severity:** info

```python
message = "This is a very very very very very very very long line"
```

### STYLE-005 – FunctionNameNotSnakeCase

```python
def MyFunction():
    pass
```

### STYLE-006 – ClassNameNotPascalCase

```python
class my_class:
    pass
```

### STYLE-007 – ConstantNotUpperCase

```python
pi_value = 3.14
```

### STYLE-008 – TrailingWhitespace

Detects trailing spaces at end of line.

### STYLE-009 – MissingBlankLineBetweenFunctions

```python
def a():
    pass
def b():
    pass
```

### STYLE-010 – MissingDocstringForFunction

```python
def process_data(data):
    return data.strip()
```

### STYLE-011 – MissingDocstringForClass

```python
class UserService:
    pass
```

### STYLE-012 – MissingDocstringForModule

Detects modules without a module-level docstring.

## SEM rules

### SEM-001 – AlwaysTrueConditionIf

```python
if 1:
    print("always")
```

### SEM-002 – AlwaysTrueConditionWhile

```python
while True:
    break
```

### SEM-003 – CompareToNoneUsingEq

```python
if value == None:
    pass
```

Preferred:

```python
if value is None:
    pass
```

### SEM-004 – AssignmentInCondition

```python
if (n := get_value()):
    print(n)
```

### SEM-005 – RedeclaredVariable

```python
count = 1
count = 2
```

### SEM-006 – ExceptionNotUsed

```python
try:
    risky()
except ValueError as e:
    print("failed")
```

### SEM-007 – BareExcept

```python
try:
    risky()
except:
    pass
```

### SEM-008 – MutableDefaultArgument

```python
def add_item(item, bucket=[]):
    bucket.append(item)
    return bucket
```

### SEM-009 – PrintDebugStatement

```python
print("debug:", value)
```

## SEC rules

### SEC-001 – UseOfEval

```python
result = eval(user_input)
```

### SEC-002 – EvalLiteralParsingCandidate

```python
data = eval("[1, 2, 3]")
```

### SEC-003 – UseOfOsSystem

```python
import os
os.system("rm -rf /tmp/test")
```

### SEC-004 – HardcodedPasswordOrKey

```python
password = "admin123"
api_key = "secret-key"
```

### SEC-005 – InsecureRandom

```python
import random
token = str(random.randint(1000, 9999))
```

### SEC-006 – OpenWithoutWith

```python
f = open("data.txt")
content = f.read()
```

Preferred:

```python
with open("data.txt") as f:
    content = f.read()
```

## PERF rules

### PERF-001 – PrintInListComprehension

```python
[print(x) for x in items]
```

### PERF-002 – UselessComprehension

```python
[x for x in items]
```

### PERF-003 – RedundantSortBeforeMinMax

```python
smallest = sorted(values)[0]
```

### PERF-004 – UnnecessaryCopy

```python
items2 = list(items)
```

### PERF-005 – DoubleLoopSameCollection

```python
for x in items:
    process_a(x)

for x in items:
    process_b(x)
```

### PERF-006 – LoopCouldBeComprehension

```python
result = []
for x in items:
    result.append(x * 2)
```

### PERF-007 – JoinOnGenerator

```python
",".join(str(x) for x in items)
```

## DEAD rules

### DEAD-001 – UnusedVariable

```python
x = 10
return 5
```

### DEAD-002 – UnreachableCode

```python
def f():
    return 1
    print("never runs")
```

### DEAD-003 – Unused assignment

```python
def f():
    x = print("hello")
    return 1
```

## CX rules

### CX-001 – TooManyArguments

```python
def create_user(name, age, city, email, phone, role, active):
    pass
```

### CX-002 – TooDeepNesting

```python
if a:
    if b:
        if c:
            if d:
                work()
```

### CX-003 – FunctionTooLong

Long functions are harder to understand, test, and maintain.

## Matcher DSL

The matcher DSL describes AST patterns declaratively.

```python
match("FunctionDef")
match("If|For|While")
```

### Basic matcher methods

```python
match("FunctionDef").has("Return")
match("FunctionDef").missing("Return")
match("FunctionDef").with_child(match("Return"))
```

### Attribute conditions

```python
match("FunctionDef").where("name", "foo")
match("FunctionDef").where_exists("doc")
match("FunctionDef").where_missing("doc")
match("FunctionDef").where_regex("name", r"^[a-z_][a-z0-9_]*$")
match("FunctionDef").where_len("args.args", 2)
match("Assign").where_node_type("value", "Call")
```

### Call matching

```python
match("Call").where_call(name="print")
match("Call").where_call(qual="os.system")
```

### Parent matching

```python
match("Call").has_parent("Expr")
match("Call").missing_parent("With|AsyncWith")
```

### Descendant matching

```python
match("FunctionDef").with_descendant(match("Call").where_call(name="print"))
match("FunctionDef").without_descendant(match("Raise"))
```

### Sequence matching

```python
match("Assign").next_sibling(match("Assign"))
match("Assign").previous_sibling(match("Assign"))
match("Assign").later_in_block(match("Expr"))
```

### Logical composition

```python
match("FunctionDef").and_(match("FunctionDef").where("name", "foo"))
match("ClassDef").or_(match("FunctionDef"))
match("FunctionDef").not_()
```

### Custom predicates

```python
def is_large_function(node):
    return len(node.body) > 10

match("FunctionDef").satisfies(is_large_function)
```

Prefer declarative matcher methods when possible.

### DSL sugar helpers

```python
match("FunctionDef").missing_docstring()
match("Module").missing_module_docstring()
match("Assign").is_unused()
match("FunctionDef").multiple_returns()
match("If").redundant_else_after_terminal()
match("Module").line_too_long(100)
match("FunctionDef").name_not_snake()
match("ClassDef").name_not_pascal()
match("Assign|AnnAssign").constant_name_not_upper()
match("FunctionDef").where_mutable_default_argument()
```

## Custom rules

Custom rules are normal subclasses of `Rule`.

```python
from astanalyzer.enums import Severity, RuleCategory, NodeType
from astanalyzer.fixer import fix
from astanalyzer.matcher import match
from astanalyzer.rule import Rule


class MyCustomRule(Rule):
    id = "CUST-001"
    title = "Detect foo function"
    severity = Severity.INFO
    category = RuleCategory.STYLE
    node_type = NodeType.FUNCTION_DEF

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("FunctionDef").where("name", "foo")
        ]
        self.fixer_builders = [
            fix().comment_before("Custom rule triggered")
        ]
```

Load custom rules:

```bash
astanalyzer scan . --rules ./my_rules.py
astanalyzer scan . --rules ./my_rules
astanalyzer scan . --rules ./team_rules --rules ./personal_rules.py
```

---

[Back to README](../README.md) | [Previous: CLI](cli.md) | [Next: Fixes](fixes.md)
EOF

cat > docs/fixes.md <<'EOF'
# Fixes

[Back to README](../README.md) | [Previous: Rules](rules.md) | [Next: Architecture](architecture.md)

## Fixer DSL

The fixer DSL builds suggested source-code changes.

```python
from astanalyzer.fixer import fix

fix()
```

A fixer records actions and a human-readable reason.

## Common fixer actions

### Insert or prepend lines

```python
fix().insert_before("x = 1")
fix().insert_after("return x")
fix().prepend("x = 1")
fix().append("return x")
fix().insert_at_body_start("result = []")
```

### Replace code

```python
fix().replace_with("pass")
fix().replace_line("return value")
fix().replace_node_text("None")
fix().replace_range("x is None")
fix().replace_with_value()
```

### Comments and docstrings

```python
fix().comment_before("TODO: review this")
fix().comment_after("Consider refactoring")
fix().comment_on_function("TODO: simplify branching")
fix().add_docstring('"""TODO: Add docstring."""')
fix().add_module_docstring('"""TODO: Add module docstring."""')
```

### Remove code

```python
fix().remove_line()
fix().delete_node()
fix().remove_statement()
fix().remove_dead_code_after()
fix().remove_node(ref="previous_assign")
```

### Block restructuring

```python
fix().remove_block_header("orelse").unindent_block("orelse", spaces=4)
fix().remove_orelse_header().unindent_orelse()
fix().flatten_always_true_if()
```

### Formatting

```python
fix().strip_trailing_whitespace()
fix().insert_blank_line_before()
```

### Targeted semantic fixes

```python
fix().replace_none_comparison_operator()
fix().remove_except_alias()
fix().replace_bare_except_with_exception()
fix().replace_mutable_default_with_none().insert_mutable_default_guard()
fix().replace_print_listcomp_with_for_loop()
fix().remove_redundant_sorted()
fix().replace_unnecessary_copy()
fix().replace_join_listcomp_with_generator()
fix().replace_eval_with_literal_eval()
fix().replace_os_system_with_subprocess_run()
fix().ensure_import("subprocess")
```

## Reasons

Every fixer should explain why it exists:

```python
fix()
    .comment_before("Debug print statement detected.")
    .because("Print statements should not remain in production code.")
```

## Custom actions

```python
fix().custom(my_callback, option="value")
```

## Refactor DSL

The refactor DSL is intended for broader project-wide transformations.

```python
from astanalyzer.refactor import refactor_builder

refactor_builder()
```

Supported operations:

```python
refactor_builder().rename_function_project_wide()
refactor_builder().rename_class_project_wide()
refactor_builder().rename_constant_project_wide()
```

These operations currently support renaming across:

- the defining file
- simple imports
- qualified usage

## Naming helpers

```python
to_snake_case("MyFunction")      # -> "my_function"
to_pascal_case("my_class")       # -> "MyClass"
to_upper_snake_case("myConst")   # -> "MY_CONST"
```

## Notes

- Fixers are primarily line-based, not full AST rewriters.
- Some actions affect only the matched node.
- Some actions switch to full-file mode, such as imports.
- Fix suggestions may still require human review.
- Refactors are broader and potentially riskier than ordinary fixers.

---

[Back to README](../README.md) | [Previous: Rules](rules.md) | [Next: Architecture](architecture.md)
EOF

cat > docs/architecture.md <<'EOF'
# Architecture

[Back to README](../README.md) | [Previous: Fixes](fixes.md) | [Next: Report UI](report-ui.md)

## Workflow

AstAnalyzer supports a full workflow from analysis to controlled code modification:

```text
scan -> select -> patch -> validate -> apply/archive
```

The workflow deliberately separates detection from modification.

## Scan the project

```bash
astanalyzer scan .
```

This generates:

- `scan_report.json`
- `report.html`

Each fix proposal can include a precomputed patch preview, allowing users to inspect changes before generating patch files or modifying source code.

The scan output includes metadata such as:

- severity
- rule identifier
- source location
- code snippet context
- snippet truncation information
- project root

## Select fixes

Open `report.html`, inspect findings, select desired fixes, and export the selected JSON plan.

The generated HTML report is standalone and has no backend dependency.

## Generate patches

```bash
astanalyzer patch
```

or:

```bash
astanalyzer patch --selected path/to/selected.json
```

This step:

- reads selected fixes
- builds patch files
- does not modify source code yet
- validates generated patches with `git apply --check`

## Apply patches

```bash
astanalyzer apply
```

If all checks pass:

- patches are applied to files
- source files are modified
- artifacts and patches are archived

## Archive run

Artifacts can be archived:

- automatically after a successful apply
- manually without applying patches

```bash
astanalyzer archive
```

## Internals

The current implementation uses an import-based plugin model:

- rules are discovered through module import side effects
- built-in rules are loaded first
- custom rule files can be imported dynamically
- rule classes are registered automatically

## Patch creation

- Fix DSL is transformed into a `FixProposal`.
- `FixProposal.get_diff()` generates a unified diff.
- Patch files are written to disk.
- Patches are validated before application.

## Design goals

- safe: no direct mutation during scan
- reviewable: diff-based workflow
- CI-friendly: patch files are portable
- reversible: git handles rollback
- robust: handles paths and artifacts outside project root

## Common pitfalls

- patches may fail if files changed after scan
- missing newline at EOF can break patch application
- older versions may fail on mismatched relative paths
- patches require a git repository, which is strongly recommended

---

[Back to README](../README.md) | [Previous: Fixes](fixes.md) | [Next: Report UI](report-ui.md)
EOF

cat > docs/report-ui.md <<'EOF'
# Report UI

[Back to README](../README.md) | [Previous: Architecture](architecture.md) | [Next: Patch System](patch-system.md)

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
EOF

cat > docs/patch-system.md <<'EOF'
# Patch System

[Back to README](../README.md) | [Previous: Report UI](report-ui.md) | [Next: Path Resolution](path-resolution.md)

## Generate patches

```bash
astanalyzer patch
```

or explicitly:

```bash
astanalyzer patch --selected path/to/selected.json
```

This step:

- reads selected fixes
- builds patch files
- does not modify source code yet
- validates generated patches using `git apply --check`

The selected JSON contains the original `project_root`, which is used to resolve source files and patch locations.

## Validate patches

Validation is automatically executed during patch generation.

It can also be done manually:

```bash
astanalyzer apply --check
```

This ensures that:

- the patch is syntactically valid
- the patch can be applied cleanly
- no conflicts exist

## Apply patches

```bash
astanalyzer apply
```

If all checks pass:

- patches are applied to files
- source files are modified
- generated artifacts are archived

## Archive generated artifacts without applying patches

```bash
astanalyzer archive
```

The archive command can also receive an explicit selected JSON file:

```bash
astanalyzer archive path/to/astanalyzer-selected.json
```

When a selected JSON file is available, AstAnalyzer reads its `project_root` value and uses it to locate generated patch files.

## Selected JSON lookup order

The archive command looks for selected JSON in this order:

1. explicitly provided path
2. `astanalyzer-selected.json` in the current working directory
3. `selected.json` in the current working directory
4. fallback to the current working directory

## Archive structure

Generated artifacts are moved into:

```text
used_patches/<timestamp>/
```

Archived artifacts may include:

- selected JSON
- scan report
- HTML report
- generated patch files

Patch files are stored under:

```text
used_patches/<timestamp>/patches/
```

The original patch directory structure is preserved relative to the detected project root.

## Clean workspace

```bash
astanalyzer clean
```

Optionally:

```bash
astanalyzer clean --include-archive
```

This removes:

- selected JSON
- scan report
- HTML report
- patch files
- `used_patches/` when `--include-archive` is used

---

[Back to README](../README.md) | [Previous: Report UI](report-ui.md) | [Next: Path Resolution](path-resolution.md)
EOF

cat > docs/path-resolution.md <<'EOF'
# Path Resolution

[Back to README](../README.md) | [Previous: Patch System](patch-system.md) | [Next: Basic Rule Example](examples/basic-rule.md)

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

[Back to README](../README.md) | [Previous: Patch System](patch-system.md) | [Next: Basic Rule Example](examples/basic-rule.md)
EOF

cat > docs/examples/basic-rule.md <<'EOF'
# Basic Rule Example

[Back to README](../../README.md) | [Previous: Path Resolution](../path-resolution.md) | [Next: Advanced Matcher](advanced-matcher.md)

## Detect a function named `foo`

This example shows a minimal custom rule.

```python
from astanalyzer.enums import Severity, RuleCategory, NodeType
from astanalyzer.fixer import fix
from astanalyzer.matcher import match
from astanalyzer.rule import Rule


class MyCustomRule(Rule):
    id = "CUST-001"
    title = "Detect foo function"
    severity = Severity.INFO
    category = RuleCategory.STYLE
    node_type = NodeType.FUNCTION_DEF

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("FunctionDef").where("name", "foo")
        ]
        self.fixer_builders = [
            fix()
            .comment_before("Custom rule triggered")
            .because("The function name matches the custom rule condition.")
        ]
```

## Load the rule

```bash
astanalyzer scan . --rules ./my_rules.py
```

## Notes

- Custom rules must subclass `Rule`.
- Rules are registered when imported.
- Prefer declarative matcher chains over custom Python predicates.
- Always provide a clear fix reason with `because(...)`.

---

[Back to README](../../README.md) | [Previous: Path Resolution](../path-resolution.md) | [Next: Advanced Matcher](advanced-matcher.md)
EOF

cat > docs/examples/advanced-matcher.md <<'EOF'
# Advanced Matcher Example

[Back to README](../../README.md) | [Previous: Basic Rule Example](basic-rule.md)

## Detect comparison to `None` using equality operators

This example detects code such as:

```python
if value == None:
    pass
```

Preferred form:

```python
if value is None:
    pass
```

## Rule implementation

```python
class CompareToNoneUsingEq(Rule):
    """
    Comparison to None using '==' or '!='.

    In Python, None should be compared using 'is' or 'is not', not equality
    operators.
    """
    id = "SEM-003"
    title = "Comparison to None using == or !="
    severity = Severity.WARNING
    category = RuleCategory.SEMANTIC
    node_type = NodeType.COMPARE

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Compare").where_compare_pairwise(
                op_in=("Eq", "NotEq"),
                any_side_value=None,
            )
        ]
        self.fixer_builders = [
            fix()
            .replace_none_comparison_operator()
            .because("Use 'is' or 'is not' when comparing with None."),
        ]
```

## Why this rule is useful

Using `== None` or `!= None` can behave incorrectly when objects override equality semantics.

The rule catches this pattern and proposes a safer Python idiom.

## Missing docstring example

```python
class MissingDocstringForFunction(Rule):
    """
    Function is missing a docstring.
    """
    id = "STYLE-010"
    title = "Missing docstring for function"
    severity = Severity.WARNING
    category = RuleCategory.STYLE
    node_type = NodeType.FUNCTION_DEF

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("FunctionDef").missing_docstring()
        ]
        self.fixer_builders = [
            fix()
            .add_docstring('"""TODO: Describe the function, its parameters and return value."""')
            .because("Function is missing a docstring."),
        ]
```

---

[Back to README](../../README.md) | [Previous: Basic Rule Example](basic-rule.md)
EOF

echo "Documentation files generated."