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
