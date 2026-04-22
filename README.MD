# astanalyzer

AST-based static analysis engine for Python with a declarative DSL for rules and automated fixes.

## What is AstAnalyzer?

AstAnalyzer is a static analysis engine for Python that operates on the abstract syntax tree (AST) and provides a declarative domain-specific language (DSL) for defining detection rules and code transformations.

Instead of modifying code directly, it generates fix proposals that can be reviewed and applied safely. The workflow separates analysis, selection, patch generation, and application into distinct stages.

The implementation ensures consistent handling of relative and absolute paths across all stages of the pipeline. This allows patch generation to work correctly even when intermediate artifacts (such as JSON reports) are located outside of the project root, improving robustness in practical usage scenarios.

This design enables reproducible analysis, integration with CI workflows, and controlled refactoring of large codebases. The tool provides full visibility into proposed changes through precomputed patch previews.

Unlike traditional linters, AstAnalyzer focuses on extensibility and controlled code transformation.

## Why this matters

Most static analysis tools produce reports that require manual inspection
and direct navigation to source code.

AstAnalyzer introduces a review step between analysis and modification,
where findings are presented with context and fix proposals can be selected
before any changes are applied.

Each proposal includes a preview of the exact code changes, making the process
transparent and reducing the risk of unintended modifications.

This makes automated refactoring safer, more transparent, and easier to control.

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

By default, the tool scans the project with all loaded rules and focuses on warnings and errors in its output:

```bash
astanalyzer scan ./project
```

### Running without installed CLI entrypoint
If you are running the module directly, the same flags work: 
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

This option is useful when you want to inspect:
- matched rules
- general findings
- patch selection flow
- file resolution
- cleanup operations

### Quiet mode
Use --quiet to show only errors:
```bash
astanalyzer --quiet scan ./project
```

## Rule selection during scan

AstAnalyzer allows selective execution of rules during the scan phase.

This is useful when you want to:
- focus on a specific rule
- suppress noisy categories temporarily
- combine broad exclusions with explicit rule overrides
- ignore unimportant directories such as test suites

### Run only selected rules

Run the scan with only specific rule IDs:

```bash
astanalyzer scan . --only STYLE-010,STYLE-011
```

### Exclude selected rules

Run all available rules except the excluded ones:

```bash
astanalyzer scan . --exclude SEC-003,SEC-006
```

### Run only selected categories

Restrict the scan to one or more rule categories:

```bash
astanalyzer scan . --only-category STYLE,SEC
```

### Exclude selected categories

Skip one or more categories during scan:

```bash
astanalyzer scan . --exclude-category STYLE
```

### Re-include specific rules after exclusion

Rules excluded by `--exclude` or `--exclude-category` can be explicitly added back using `--include`:

```bash
astanalyzer scan . --exclude-category STYLE --include STYLE-010
```

### Ignore selected directories

Directory names can be excluded from the scan:

```bash
astanalyzer scan . --exclude-dir tests,venv,migrations
```

### Notes on filter behavior

Rule filters are applied in the following order:

1. `--only`
2. `--only-category`
3. `--exclude`
4. `--exclude-category`
5. `--include`

This means that `--include` can restore rules that were previously excluded.

Examples:

```bash
astanalyzer scan . --only STYLE-010
```

```bash
astanalyzer scan . --exclude-category STYLE --include STYLE-010
```

---

## How it works (scan -> select -> patch -> apply)

AstAnalyzer supports a full workflow from analysis to automated code modification.

### Scan the project 
```bash
astanalyzer scan .
```
This generates:
- `scan_report.json`
- `report.html` (interactive UI for selecting fixes)

Each fix proposal also includes a **precomputed patch preview** (unified diff),
allowing users to inspect the exact code changes directly in the report
without generating patch files or modifying source code.

The scan output includes structured metadata for each finding, including:
- severity
- rule identifier
- location
- code snippet context
- snippet truncation information

This metadata is used by the UI to provide accurate visualization without
modifying the original code representation.

### Select fixes (UI)

Open `report.html`, inspect findings using the interactive UI, select desired fixes, and export the selection.

The generated HTML report is a standalone interactive page with no backend dependencies.
It can be opened directly in a browser and is designed for efficient inspection and selection
of fix proposals.

The report uses hierarchical navigation. Findings are grouped by category and rule, and each
individual finding is displayed as a collapsible card.

### Report structure

The HTML report groups findings hierarchically:

- Category → Rule → Findings

Rule descriptions are displayed at the rule level and are not repeated for each finding.
They are shown on demand (collapsible), which reduces visual noise and improves navigation
in large analysis outputs.

#### Hierarchical grouping

To improve navigation in large projects, findings are grouped into a three-level hierarchy:

- **Category** (e.g. STYLE, SEC, CX)
- **Rule**
- **Individual findings**

Each level is collapsible, allowing users to efficiently navigate large numbers of findings.

Additionally, each category and rule shows:
- total number of findings
- breakdown by severity (info / warning / error)

This significantly reduces cognitive load compared to a flat list and makes it easier to:
- identify dominant problem areas
- inspect issues per rule
- work efficiently with large reports

**Collapsed view (finding overview):**
- finding identifier (e.g. F-001)
- severity
- rule ID
- file path and line range

**Expanded view (finding details):**
- syntax-highlighted code snippet with surrounding context
- highlighted lines where the issue occurs
- available fix proposals with human-readable explanations
- optional suppression action (ignore directive)

#### Rule-level details

Each rule provides:
- rule identifier and title
- aggregated statistics (number of findings and severity distribution)
- collapsible rule description

This separation ensures that general explanations are shown once,
while findings focus only on concrete occurrences.

#### Guided navigation

The interface encourages exploration through:
- expandable categories and rules
- contextual hints (e.g. "Expand categories to explore findings")
- progressive disclosure of details

This approach reduces cognitive load when working with large reports.

#### Severity awareness

Findings are visually distinguished by severity:

- **info** – low importance, informational suggestions
- **warning** – actionable issues (default focus)
- **error** – critical problems requiring immediate attention

Severity is reflected in:
- color-coded labels
- aggregated counts per category and per rule
- visual highlighting (left border indicators)

This allows users to quickly identify high-impact issues and prioritize fixes.

#### Code snippet preview

The report includes a contextual code preview that:

- shows surrounding lines around the issue
- highlights the exact affected lines
- uses syntax highlighting (Pygments)
- indicates when the snippet is truncated

Truncation is represented as metadata and rendered explicitly in the UI,
instead of being embedded directly into the code snippet. This preserves
correct line mapping and keeps the preview clean.

This significantly improves readability compared to raw JSON output and allows
understanding issues without opening the source file.

#### Fix proposals

Each fix is presented with:
- a short title
- optional explanation (reason)
- human-readable description of actions derived from DSL
- **patch preview (unified diff)**
- expandable technical detail (raw DSL)

#### Patch preview

Each fix proposal includes a precomputed patch preview displayed directly in the report.

The preview is generated during the scan phase and represents the exact unified diff
that would be produced during patch generation.

This allows users to:

- inspect the exact code changes before selecting a fix
- understand the scope of modifications without opening source files
- compare multiple fix proposals quickly

The preview uses a unified diff format with basic highlighting:

- added lines (`+`)
- removed lines (`-`)
- diff metadata and context (`@@`, file headers)

If a preview cannot be generated (e.g. no effective change), the UI displays
a clear fallback message explaining the reason.

The preview is a read-only artifact and does not modify code or create patch files.

#### Additional actions

Each finding supports:
- **"Suppress this warning"** action
  - inserts an ignore directive into the source code
  - allows selective suppression directly from UI

#### Interaction features

The report supports:
- full-text filtering (rule, file, message, fix text)
- bulk selection of fixes
- clearing selection
- exporting selected fixes into a JSON plan
- hierarchical navigation (category → rule → findings)

The exported JSON is then used in the patch generation step.

### Generate patches
```bash
astanalyzer patch
```
or explicitly:

```bash
astanalyzer patch --selected path/to/selected.json
```

This step:
- reads selected fixes
- builds patch files (`*.patch`)
- does **not** modify source code yet

The patch command supports explicit input of the selected JSON file and does not require it to be located in the project root. File paths are resolved relative to the project, ensuring consistent behavior across different environments.

### Path handling and robustness

The tool does not assume that analysis artifacts (e.g. `scan_report.json` or selected JSON files) are located within the project root.

All paths are normalized and resolved consistently during patch generation and application. This prevents failures caused by mismatched relative paths and allows flexible workflows where analysis results are stored or processed externally.

This behavior was introduced to eliminate common sources of patch failure in earlier versions.

### Validate patches (dry-run)
Validation is automatically executed during patching, but can also be done manually:
```bash
astanalyzer apply --check
```

This ensures:
- the patch is syntactically valid
- the patch can be applied cleanly
- no conflicts exist

### Apply patches
```bash
astanalyzer apply
```
If all checks pass:
- patches are applied to files
- source files are modified

### Archive run
After a successful apply, the following artifacts are moved to:
- selected JSON 
- scan report
- HTML report
- patch files

are moved to: 
```bash
used_patches/<timestamp>/
```

### Clean workspace
```bash
astanalyzer clean
```
Optionally:
```bash
astanalyzer clean --include-archive
```
This removes the following artifacts:
- selected JSON 
- scan report
- HTML report
- patch files
- `used_patches/` when `--include-archive` is used

---

## Ignoring findings

AstAnalyzer allows suppressing findings directly in code using inline comments.

Use this only when the code is intentional and acceptable.

Ignore directives are preserved in the source code and will suppress findings in future scans.

---

### Ignore next node

Suppress a rule for the following statement:

```python
# astanalyzer: ignore-next STYLE-003
def foo():
    ...
```

---

### Ignore on the same line

```python
x = eval(data)  # astanalyzer: ignore SEC-030
```

---

### Ignore multiple rules

```python
# astanalyzer: ignore-next STYLE-003, FUNC-001
def foo():
    ...
```

---

### Disable rules in a block

```python
# astanalyzer: disable STYLE-003

def foo():
    ...

# astanalyzer: enable STYLE-003
```

---

### Ignore all rules

```python
# astanalyzer: ignore-next
def foo():
    ...
```

---

## Built-in Rules

This project includes a set of built-in static analysis rules for Python code.
The rules are grouped into six categories:

- `STYLE` – Code style, formatting, readability, naming and documentation
- `SEM` – Semantic issues and suspicious or misleading logic
- `SEC` – Security-related patterns and risks
- `PERF` – Performance and efficiency issues and inefficient constructs
- `DEAD` – Dead code and unreachable logic
- `CX` – Complexity and maintainability problems

Rules are identified by a stable rule ID and include metadata such as severity and title.

### Rule ID format

Each rule is identified by a stable ID in the following format:

```
<CATEGORY>-<NUMBER>
```

Examples:
- `STYLE-004`
- `SEC-001`
- `CX-003`

#### Categories

- `STYLE` – Code style, formatting, naming and documentation
- `SEM` – Semantic issues and suspicious logic
- `SEC` – Security-related patterns and risks
- `PERF` – Performance and efficiency issues
- `DEAD` – Dead code and unreachable logic
- `CX` – Complexity and maintainability problems

#### Numbering

- Numbers are sequential within each category (e.g. `STYLE-001`, `STYLE-002`, ...)
- IDs are stable and should not change once released
- Removed rules should not reuse existing IDs

#### Purpose

Rule IDs are used for:
- identifying findings in reports
- filtering and grouping issues
- selecting rules from CLI (`--only`, `--exclude`, `--include`)
- referencing rules in CI pipelines and tooling
- mapping fixes and patches to specific rules
---
## STYLE – Code Style & Readability Rules

### STYLE-001 – EmptyBlock
**Severity:** warning  
Detects blocks that are syntactically present but effectively empty.

```python
if ready:
    pass
```
---
### STYLE-002 – RedundantIfElseReturn
**Severity:** info  
Detects `if/else` returning boolean literals.

```python
def is_valid(x):
    if x > 0:
        return True
    else:
        return False
```

---

### STYLE-003 – MultipleReturnsInFunction
**Severity:** info  
Detects functions with multiple return statements.

```python
def classify(x):
    if x < 0:
        return "neg"
    if x == 0:
        return "zero"
    return "pos"
```

---

### STYLE-004 – LineTooLong
**Severity:** info  
Detects lines exceeding configured length.

```python
message = "This is a very very very very very very very long line"
```

---

### STYLE-005 – FunctionNameNotSnakeCase
**Severity:** info  

```python
def MyFunction():
    pass
```

---

### STYLE-006 – ClassNameNotPascalCase
**Severity:** info  

```python
class my_class:
    pass
```

---

### STYLE-007 – ConstantNotUpperCase
**Severity:** info  

```python
pi_value = 3.14
```

---

### STYLE-008 – TrailingWhitespace
**Severity:** info  
Detects trailing spaces at end of line.

---

### STYLE-009 – MissingBlankLineBetweenFunctions
**Severity:** info  

```python
def a():
    pass
def b():
    pass
```

---

### STYLE-010 – MissingDocstringForFunction
**Severity:** warning  

```python
def process_data(data):
    return data.strip()
```

---

### STYLE-011 – MissingDocstringForClass
**Severity:** warning  

```python
class UserService:
    pass
```

---

### STYLE-012 – MissingDocstringForModule
**Severity:** warning  

---

## SEM – Semantic Rules

### SEM-001 – AlwaysTrueConditionIf
**Severity:** warning  

```python
if 1:
    print("always")
```

---

### SEM-002 – AlwaysTrueConditionWhile
**Severity:** warning  

```python
while True:
    break
```

---

### SEM-003 – CompareToNoneUsingEq
**Severity:** warning  

```python
if value == None:
    pass
```

Preferred:
```python
if value is None:
    pass
```

---

### SEM-004 – AssignmentInCondition
**Severity:** warning  

```python
if (n := get_value()):
    print(n)
```

---

### SEM-005 – RedeclaredVariable
**Severity:** warning  

```python
count = 1
count = 2
```

---

### SEM-006 – ExceptionNotUsed
**Severity:** info  

```python
try:
    risky()
except ValueError as e:
    print("failed")
```

---

### SEM-007 – BareExcept
**Severity:** info  

```python
try:
    risky()
except:
    pass
```

---

### SEM-008 – MutableDefaultArgument
**Severity:** warning  

```python
def add_item(item, bucket=[]):
    bucket.append(item)
    return bucket
```

---

### SEM-009 – PrintDebugStatement
**Severity:** warning  

```python
print("debug:", value)
```

---

## SEC – Security Rules

### SEC-001 – UseOfEval
**Severity:** warning  

```python
result = eval(user_input)
```

---

### SEC-002 – EvalLiteralParsingCandidate
**Severity:** info  

```python
data = eval("[1, 2, 3]")
```

---

### SEC-003 – UseOfOsSystem
**Severity:** warning  

```python
import os
os.system("rm -rf /tmp/test")
```

---

### SEC-004 – HardcodedPasswordOrKey
**Severity:** warning  

```python
password = "admin123"
api_key = "secret-key"
```

---

### SEC-005 – InsecureRandom
**Severity:** warning  

```python
import random
token = str(random.randint(1000, 9999))
```

---

### SEC-006 – OpenWithoutWith
**Severity:** warning  

```python
f = open("data.txt")
content = f.read()
```

Preferred:
```python
with open("data.txt") as f:
    content = f.read()
```

---

## PERF – Performance Rules

### PERF-001 – PrintInListComprehension
**Severity:** warning  

```python
[print(x) for x in items]
```

---

### PERF-002 – UselessComprehension
**Severity:** warning  

```python
[x for x in items]
```

---

### PERF-003 – RedundantSortBeforeMinMax
**Severity:** warning  

```python
smallest = sorted(values)[0]
```

---

### PERF-004 – UnnecessaryCopy
**Severity:** info  

```python
items2 = list(items)
```

---

### PERF-005 – DoubleLoopSameCollection
**Severity:** info  

```python
for x in items:
    process_a(x)

for x in items:
    process_b(x)
```

---

### PERF-006 – LoopCouldBeComprehension
**Severity:** info  

```python
result = []
for x in items:
    result.append(x * 2)
```

---

### PERF-007 – JoinOnGenerator
**Severity:** info  

```python
",".join(str(x) for x in items)
```

---

## DEAD – Dead Code Rules

### DEAD-001 – UnusedVariable
**Severity:** warning  

```python
x = 10
return 5
```

---

### DEAD-002 – UnreachableCode
**Severity:** warning  

```python
def f():
    return 1
    print("never runs")
```

---

### DEAD-003 – Unused assignment (keep value)
**Severity:** warning  

```python
def f():
    x = print("hello")
    return 1
```

---

## CX – Complexity Rules

### CX-001 – TooManyArguments
**Severity:** warning  

```python
def create_user(name, age, city, email, phone, role, active):
    pass
```

---

### CX-002 – TooDeepNesting
**Severity:** warning  

```python
if a:
    if b:
        if c:
            if d:
                work()
```

---

### CX-003 – FunctionTooLong
**Severity:** warning  

```python
def big_function():
    ...
```

Long functions are harder to understand, test, and maintain.

---

## Rule DSL

### Matcher DSL
The matcher DSL is used to describe AST patterns declaratively.

Create a matcher with:
```python
match("FunctionDef")
match("If|For|While")
```
A matcher can then be refined with additional conditions.



#### Basic matcher methods
Match by type
```python
match("FunctionDef")
match("Assign|AnnAssign")
```
Child existence
```python
match("FunctionDef").has("Return")
match("FunctionDef").missing("Return")
match("FunctionDef").with_child(match("Return"))
```
#### Attribute conditions
```python
match("FunctionDef").where("name", "foo")
match("FunctionDef").where_exists("doc")
match("FunctionDef").where_missing("doc")
match("FunctionDef").where_regex("name", r"^[a-z_][a-z0-9_]*$")
match("FunctionDef").where_len("args.args", 2)
match("Assign").where_node_type("value", "Call")
```
#### Call matching
```python
match("Call").where_call(name="print")
match("Call").where_call(qual="os.system")
```
#### Parent matching
```python
match("Call").has_parent("Expr")
match("Call").missing_parent("With|AsyncWith")
```
#### Descendant matching
```python
match("FunctionDef").with_descendant(match("Call").where_call(name="print"))
match("FunctionDef").without_descendant(match("Raise"))
```
#### Sequence matching
```python
match("Assign").next_sibling(match("Assign"))
match("Assign").previous_sibling(match("Assign"))
match("Assign").later_in_block(match("Expr"))

```
#### Logical composition
```python
match("FunctionDef").and_(match("FunctionDef").where("name", "foo"))
match("ClassDef").or_(match("FunctionDef"))
match("FunctionDef").not_()
```

#### Custom predicates

If built-in matcher methods are not sufficient, you can provide a custom predicate:

```python
match("FunctionDef").satisfies(lambda node: ...)
```

You can also use a named function:

```python
def is_large_function(node):
    return len(node.body) > 10

match("FunctionDef").satisfies(is_large_function)
```

Custom predicates allow arbitrary logic, but should be used sparingly.
Prefer declarative matcher methods when possible.

#### Captures and references

Captures store matched objects into the matching context so they can be reused later.
```python
match("For").capture_ancestor("outer", "For").same_iter_as_ancestor("outer")
```
#### DSL sugar helpers
The project also provides convenience methods for common checks:

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
#### Special matcher helpers currently supported
Examples of special conditions used in existing rules:
```python
match("Compare").where_compare_pairwise(op_in=("Eq", "NotEq"), any_side_value=None)
match("If|While").where_contains("NamedExpr", in_="test")
match("Assign|AnnAssign").where_target_contains_any("password", "token", "secret")
match("Assign|AnnAssign").where_value_is_string_literal(non_empty=True)
match("ExceptHandler").where_except_binds_name(ignore="_")
match("ExceptHandler").where_body_missing_name("")
```

#### Notes
- Matchers operate on astroid nodes
- Most matcher methods are best-effort and intentionally lightweight
- Prefer declarative matcher chains over imperative logic
--- 
### Fixer DSL 

The fixer DSL is used to build suggested source-code changes.

Create a fixer with:
```python
from astanalyzer.fixer import fix

fix()
```
A fixer records actions and a human-readable reason.

#### Common fixer actions
Insert or prepend lines
```python
fix().insert_before("x = 1")
fix().insert_after("return x")
fix().prepend("x = 1")
fix().append("return x")
fix().insert_at_body_start("result = []")
```

#### Replace code
```python
fix().replace_with("pass")
fix().replace_line("return value")
fix().replace_node_text("None")
fix().replace_range("x is None")
fix().replace_with_value()
```

#### Comments and docstrings
```python
fix().comment_before("TODO: review this")
fix().comment_after("Consider refactoring")
fix().comment_on_function("TODO: simplify branching")
fix().add_docstring('"""TODO: Add docstring."""')
fix().add_module_docstring('"""TODO: Add module docstring."""')
```

#### Remove code
```python
fix().remove_line()
fix().delete_node()
fix().remove_statement()
fix().remove_dead_code_after()
fix().remove_node(ref="previous_assign")
```

#### Block restructuring
```python
fix().remove_block_header("orelse").unindent_block("orelse", spaces=4)
fix().remove_orelse_header().unindent_orelse()
fix().flatten_always_true_if()
```

#### Formatting
```python
fix().strip_trailing_whitespace()
fix().insert_blank_line_before()
```

#### Targeted semantic fixes
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
### Reasons
Every fixer should explain why it exists:
```python
fix()
    .comment_before("Debug print statement detected.")
    .because("Print statements should not remain in production code.")
```
### Custom actions
For cases that are not yet covered by the built-in DSL:

```python
fix().custom(my_callback, option="value")
```

#### Notes
- Fixers are primarily line-based, not full AST rewriters
- Some actions affect only the matched node
- Some actions switch to full-file mode (e.g. imports)
- Fix suggestions may still require human review

---
### Refactor DSL

The refactor DSL is intended for broader project-wide transformations.

Create a refactor builder with:
```python
from astanalyzer.refactor import refactor_builder

refactor_builder()
```
#### Supported refactor operations
```python
refactor_builder().rename_function_project_wide()
refactor_builder().rename_class_project_wide()
refactor_builder().rename_constant_project_wide()
```

These operations currently support renaming across:
	•	the defining file
	•	simple imports (from module import name)
	•	qualified usage (import module + module.name(...))

#### Naming helpers
The project provides naming conversion helpers:

```python
to_snake_case("MyFunction")      # -> "my_function"
to_pascal_case("my_class")       # -> "MyClass"
to_upper_snake_case("myConst")   # -> "MY_CONST"
```

#### Notes
- Refactors are broader and potentially riskier than fixers
- They should be reviewed before applying
- Current implementation is regex/text-based (not symbol-table perfect)

---
## Rule examples

### Example: detect `== None`

```python
class CompareToNoneUsingEq(Rule):
    """
    Comparison to None using '==' or '!='.

    In Python, None should be compared using 'is' or 'is not', not equality
    operators. Using '==' or '!=' can lead to incorrect behavior if an object
    overrides equality semantics.

    Consider replacing the comparison with 'is None' or 'is not None'.
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

### Example: detect missing function docstrings
```python
class MissingDocstringForFunction(Rule):
    """
    Function is missing a docstring.

    Docstrings describe the purpose, parameters, and return values of a function.
    Without them, the code is harder to understand, use, and maintain—especially
    for other developers or future readers.

    Consider adding a clear and concise docstring.
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
## Custom rules

AstAnalyzer can load custom rules from user-provided Python files or directories.

Custom rules are normal subclasses of `Rule`. Once imported, they are registered
automatically through the rule registry.

### Writing rules
AstAnalyzer allows you to define custom static analysis rules using a simple Python-based DSL.

Rules are defined as Python classes that inherit from `Rule`.

A rule usually contains:

- metadata (`id`, `title`, `severity`, `category`, `node_type`)
- one or more `matchers` describing what should be detected
- optional `fixer_builders` describing suggested fixes
- optional refactor builders for project-wide transformations

### Example custom rule

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


### Load custom rules from CLI

You can load custom rules using the `--rules` argument.

#### Load from a single file

```bash
astanalyzer scan . --rules ./my_rules.py
```

#### Load from a directory

```bash
astanalyzer scan . --rules ./my_rules
```

All `.py` files in the directory (recursively) will be imported.

#### Load multiple rule sources

```bash
astanalyzer scan . --rules ./team_rules --rules ./personal_rules.py
```

### How it works

- Built-in rules are loaded first
- Custom rule files are imported dynamically
- Importing a module registers its rule classes automatically (via `Rule` metaclass)
- The scan then runs with both built-in and custom rules
- Custom rules can also be targeted by scan filters if they define stable rule IDs

### Notes

- Only `.py` files are imported
- Files starting with `_` are skipped when loading from a directory
- Custom rules must subclass `Rule`
- Rules are registered at import time (no manual registration needed)
- Prefer declarative matcher chains over custom logic
- Keep rules focused and single-purpose
- Always provide a clear explanation (`because(...)`) for fixes

---

## Internals (advanced)
The current implementation uses an import-based plugin model:

- Rules are discovered via module import side effects
- This keeps the system simple and flexible
- Future versions may introduce explicit plugin registries or entry-point based loading

### Patch creation

- Fix DSL is transformed into a `FixProposal`
- `FixProposal.get_diff()` generates a unified diff
- patch files are written to disk

### Patch validation
Each patch is checked using:
```bash
git apply --check
```
This verifies:
- correct diff format
- correct context lines
- file consistency


### Patch application

Patches are applied using:
```bash
git apply
```
This modifies files directly.

### Why this design?

- safe (no direct mutation during scan)
- reviewable (diff-based workflow)
- CI-friendly (patch files are portable)
- reversible (git handles rollback)
- robust (handles paths and artifacts outside project root)

### Common pitfalls
- patches fail if file changed after scan
- missing newline at EOF can break the patch (auto-fixed)
- mismatched relative paths may cause issues in earlier versions (now mitigated by consistent path resolution)
- patches require a git repository (recommended)

---

## Built-in rule groups

- `rules.style` – naming, formatting, docstrings, readability
- `rules.semantic` – logical and semantic code smells
- `rules.security` – risky APIs and insecure patterns
- `rules.performance` – unnecessary allocations and inefficient constructs
- `rules.dead_code` – unused or unreachable code
- `rules.complexity` – deep nesting and argument count issues

## Limitations

- Matchers are intentionally lightweight and best-effort
- Fixers are mostly line-based and not full AST transformations
- Refactors are approximate and should be reviewed before applying
- Some rules provide suggestions rather than automatic fixes
- Complex transformations may require custom fixers or refactor passes