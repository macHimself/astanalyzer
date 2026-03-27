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


## Writing rules
Rules are defined as Python classes that inherit from `Rule`.

A rule usually contains:

- metadata (`id`, `title`, `severity`, `category`, `node_type`)
- one or more `matchers` describing what should be detected
- optional `fixer_builders` describing suggested fixes
- optional refactor builders for project-wide transformations

Example:

```python
from astanalyzer.rule import Rule
from astanalyzer.matcher import match
from astanalyzer.fixer import fix
from astanalyzer.enums import Severity, RuleCategory, NodeType


class MissingDocstringForFunction(Rule):
    id = "STYLE-002"
    title = "Missing doc string for function"
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
                .add_docstring('"""TODO: Describe the function."""')
                .because("Function is missing a docstring.")
        ]
```

## Matcher DSL
The matcher DSL is used to describe AST patterns declaratively.

Create a matcher with:
```python
match("FunctionDef")
match("If|For|While")
```
A matcher can then be refined with additional conditions.



### Basic matcher methods
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
Attribute conditions
```python
match("FunctionDef").where("name", "foo")
match("FunctionDef").where_exists("doc")
match("FunctionDef").where_missing("doc")
match("FunctionDef").where_regex("name", r"^[a-z_][a-z0-9_]*$")
match("FunctionDef").where_len("args.args", 2)
match("Assign").where_node_type("value", "Call")
```
Call matching
```python
match("Call").where_call(name="print")
match("Call").where_call(qual="os.system")
```
Parent matching
```python
match("Call").has_parent("Expr")
match("Call").missing_parent("With|AsyncWith")
```
Descendant matching
```python
match("FunctionDef").with_descendant(match("Call").where_call(name="print"))
match("FunctionDef").without_descendant(match("Raise"))
```
Scoped matching
```python
match("Assign").next_sibling(match("Assign"))
match("Assign").previous_sibling(match("Assign"))
match("Assign").later_in_block(match("Expr"))
```
Sequence matching
```python
match("Assign").next_sibling(match("Assign"))
match("Assign").previous_sibling(match("Assign"))
match("Assign").later_in_block(match("Expr"))

```
Logical composition
```python
match("FunctionDef").and_(match("FunctionDef").where("name", "foo"))
match("ClassDef").or_(match("FunctionDef"))
match("FunctionDef").not_()
```
Captures and references

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
Matchers operate on astroid nodes.
Most matcher methods are best-effort and intentionally lightweight.
Prefer declarative matcher chains over custom imperative logic where possible.



## Fixer DSL
The fixer DSL is used to build suggested source-code changes.

Create a fixer with:
```python
from astanalyzer.fixer import fix

fix()
```
A fixer records actions and a human-readable reason.


### Common fixer actions
Insert or prepend lines
```python
fix().insert_before("x = 1")
fix().insert_after("return x")
fix().prepend("x = 1")
fix().append("return x")
fix().insert_at_body_start("result = []")
```

Replace code
```python
fix().replace_with("pass")
fix().replace_line("return value")
fix().replace_node_text("None")
fix().replace_range("x is None")
fix().replace_with_value()
```

Comments and docstrings
```python
fix().comment_before("TODO: review this")
fix().comment_after("Consider refactoring")
fix().comment_on_function("TODO: simplify branching")
fix().add_docstring('"""TODO: Add docstring."""')
fix().add_module_docstring('"""TODO: Add module docstring."""')
```

Remove code
```python
fix().remove_line()
fix().delete_node()
fix().remove_statement()
fix().remove_dead_code_after()
fix().remove_node(ref="previous_assign")
```

Block restructuring
```python
fix().remove_block_header("orelse").unindent_block("orelse", spaces=4)
fix().remove_orelse_header().unindent_orelse()
fix().flatten_always_true_if()
```

Formating
```python
fix().strip_trailing_whitespace()
fix().insert_blank_line_before()
```
Targeted semantic fixes
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

### Notes
Fixers are primarily line-based, not full AST rewriters.
Some actions rewrite only the matched node.
Some actions switch to full-file mode when the change affects imports or surrounding code.
A fixer may produce a patch suggestion even when the change still requires human review.

## Refactor DSL

The refactor DSL is intended for broader project-wide transformations.

Create a refactor builder with:
```python
from astanalyzer.refactor import refactor_builder

refactor_builder()
```
### Supported refactor operations
```python
refactor_builder().rename_function_project_wide()
refactor_builder().rename_class_project_wide()
refactor_builder().rename_constant_project_wide()
```

These operations currently support renaming across:
	•	the defining file
	•	simple imports (from module import name)
	•	qualified usage (import module + module.name(...))

The project provides naming conversion helpers:

```python
to_snake_case("MyFunction")      # -> "my_function"
to_pascal_case("my_class")       # -> "MyClass"
to_upper_snake_case("myConst")   # -> "MY_CONST"
```
### Notes
Refactors are broader and potentially riskier than ordinary fixers.
They should be reviewed before applying.
The current implementation is regex/text-based, not symbol-table-perfect.

## Rule examples


### Example: detect `== None`

```python
class CompareToNoneUsingEq(Rule):
    id = "CMP-001"
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
                .because("Use 'is' or 'is not' when comparing with None.")
        ]
```

### Example: detect missing function docstrings
```python
class MissingDocstringForFunction(Rule):
    id = "STYLE-002"
    title = "Missing doc string for function"
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
                .add_docstring('"""TODO: Describe the function."""')
                .because("Function is missing a docstring.")
        ]
```

## Notes and limitations
- The matcher DSL is intentionally lightweight and pragmatic.
- Fixers are mostly line-based and do not attempt full semantic rewriting.
- Refactors are best-effort and should be reviewed before applying.
- Some rules provide advisory comments instead of automatic rewrites.
- For complex transformations, a custom fixer or dedicated refactor pass may be needed.


## Built-in rule groups

- `rules.style` – naming, formatting, docstrings, readability
- `rules.semantic` – logical and semantic code smells
- `rules.security` – risky APIs and insecure patterns
- `rules.performance` – unnecessary allocations and inefficient constructs
- `rules.dead_code` – unused or unreachable code
- `rules.complexity` – deep nesting and argument count issues


## Custom rules

AstroAnalyzer can load custom rules from user-provided Python files or directories.

Custom rules are normal subclasses of `Rule`. Once imported, they are registered
automatically through the rule registry.

---

### Example custom rule

```python
from astanalyzer.rule import Rule
from astanalyzer.matcher import match
from astanalyzer.enums import Severity, RuleCategory, NodeType


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
```

---

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

---

### How it works

- Built-in rules are loaded first
- Custom rule files are imported dynamically
- Importing a module registers its rule classes automatically (via `Rule` metaclass)
- The scan then runs with both built-in and custom rules

---

### Notes

- Only `.py` files are imported
- Files starting with `_` are skipped when loading from a directory
- Custom rules must subclass `Rule`
- Rules are registered at import time (no manual registration needed)

---

### Design note

The current implementation uses an import-based plugin model:

- Rules are discovered via module import side effects
- This keeps the system simple and flexible
- Future versions may introduce explicit plugin registries or entry-point based loading