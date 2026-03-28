# astanalyzer

AST-based static analysis engine for Python with a declarative DSL for rules and automated fixes.

## What is AstAnalyzer?

AstAnalyzer is a static analysis engine for Python that operates on the abstract syntax tree (AST) and provides a declarative domain-specific language (DSL) for defining detection rules and code transformations.

Instead of modifying code directly, it generates patch proposals that can be reviewed and applied safely. This design enables reproducible analysis, integration with CI workflows, and controlled refactoring of large codebases.

Unlike traditional linters, AstAnalyzer focuses on extensibility and controlled code transformation.

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
If you are running the module directly, the same flags works: 
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

---

## How it works (scan -> select -> patch -> apply)

AstAnalyzer supports a full workflow from analysis to automated code modification.

### Scan the project 
```bash
astanalyzer scan .
```
This generates: 
scan_report.json, report.html (interactive UI for selecting fixes)

### Select fixes (UI)

Open `report.html`, select desired fixes, and export the selection.

### Generate patches
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


### Validate patches (dry-run)
Validation is automatically executed during patching, but can also be done manually:
```bash
astanalyzer apply --check
```
This ensures:
patch is syntactically valid
patch can be applied cleanly
no conflicts exist

### Apply patches
```bash
astanalyzer apply
```
If all checks pass: 
patches are applied to files
files are modified

### Archive run
After successful apply:
selected JSON 
scan report
HTML report
patch files

are moved to: 
```bash
used_patches/<timestamp>/
```

### Clean workspace
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
and used_patches/

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

Each rule has:
- a stable rule ID
- a severity level
- a title
- a short explanation
- an example of what it detects

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

AstroAnalyzer can load custom rules from user-provided Python files or directories.

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

### Patch creation:

Fix DSL -> transformed into FixProposal
FixProposal.get_diff() generates unified diff
Patch files are written to disk 

### Patch validation:
Each patch is checked using:
```bash
git apply --check
```
This verifies:
correct diff format
correct context lines
file consistency


### Patch application
Patches are applied using
```bash
git apply
```
This modifies files directly.

### Why this design?

- safe (no direct mutation during scan)
- reviewable (diff-based workflow)
- CI-friendly (patch files are portable)
- reversible (git handles rollback)

### Common pitfalls
- patches fail if file changed after scan
- missing newline at EOF can break the patch (auto-fixed)
- relative paths must match project structure
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