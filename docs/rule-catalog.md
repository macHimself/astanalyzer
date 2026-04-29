[Back to README](../README.md) | [Previous: Rules](rules.md) | [Next: Rule DSL](rule-dsl.md)

# Rule Catalog

## Style Rules

Style rules identify readability, formatting, naming, and documentation issues.

These rules usually do not indicate runtime bugs. Their purpose is to improve consistency, maintainability, and reviewability of the codebase. Many style findings are intentionally advisory and may be suppressed when the current form is clearer or required by external constraints.

---

### STYLE-001: Empty block

Detects control-flow blocks that contain no executable logic.

**Why it matters:**  

Empty blocks often indicate unfinished code, leftover scaffolding, or redundant control flow.

**Suggested action:**  

Add the missing logic or remove the empty block.

**Limitations:**  

Empty blocks may be intentional in placeholders, examples, abstract templates, or temporary development code.

**Severity:** warning

```python
if ready:
    pass
```

---

### STYLE-002: Redundant else after terminal branch

Detects `else` blocks following branches that already end with `return`, `raise`, `break`, or `continue`.

**Why it matters:**  

Removing the redundant `else` reduces indentation and makes the main execution path easier to follow.

**Suggested action:**  

Remove the `else` header and unindent its body.

**Limitations:**  

An explicit `else` may improve readability when two alternative branches are intentionally shown symmetrically.

**Severity:** info

```python
def is_valid(x):
    if x > 0:
        return True
    else:
        return False
```

---

### STYLE-003: Multiple returns in function

Detects functions with multiple return statements.

**Why it matters:**  

Multiple exit points can make control flow harder to follow in long or complex functions.

**Suggested action:**  

Review whether a single exit point improves readability.

**Limitations:**  

Multiple returns are often clearer when used as guard clauses or early exits.

**Severity:** info

```python
def classify(x):
    if x < 0:
        return "neg"
    if x == 0:
        return "zero"
    return "pos"
```

---

### STYLE-004: Line too long

Detects lines exceeding the configured maximum length.

**Why it matters:**  

Long lines are harder to read in diffs, reviews, terminal editors, and side-by-side views.

**Suggested action:**  

Split long expressions, extract variables, or reformat argument lists.

**Limitations:**  

Long URLs, generated code, data literals, and long strings may be clearer when kept unchanged.

**Severity:** info

```python
message = "This is a very very very very very very very long line"
```

---

### STYLE-005: Function name not in snake_case

Detects function names that do not follow `snake_case`.

**Why it matters:**  

Consistent function naming improves readability and aligns code with common Python conventions.

**Suggested action:**  

Rename the function and update references.

**Limitations:**  

Non-snake-case names may be required by framework hooks, external APIs, generated code, or compatibility layers.

```python
def MyFunction():
    pass
```

---

### STYLE-006: Class name not in PascalCase

Detects class names that do not follow `PascalCase`.

**Why it matters:**  

Consistent class naming helps distinguish classes from functions, modules, and variables.

**Suggested action:**  

Rename the class and update references.

**Limitations:**  

Non-standard names may be required by generated code, external schemas, compatibility layers, or framework conventions.

```python
class my_class:
    pass
```

---

### STYLE-007: Constant not in UPPER_SNAKE_CASE

Detects constants whose names do not follow `UPPER_SNAKE_CASE`.

**Why it matters:**  

Uppercase names signal stable module-level values and help distinguish constants from ordinary variables.

**Suggested action:**  

Rename true constants to `UPPER_SNAKE_CASE`.

**Limitations:**  

This rule may produce false positives for normal module-level variables, mutable values, Sphinx configuration variables, generated code, or values intentionally reassigned later.

```python
pi_value = 3.14
```

---

### STYLE-008: Trailing whitespace

Detects whitespace at the end of a line.

**Why it matters:**  

Trailing whitespace creates unnecessary diff noise and may conflict with formatters or editor settings.

**Suggested action:**  

Remove trailing whitespace.

**Limitations:**  

Trailing spaces may be intentional in text fixtures, snapshot tests, generated files, or examples where exact whitespace matters.

---

### STYLE-009: Missing blank line between definitions

Detects function definitions that are not separated by expected blank lines.

**Why it matters:**  

Blank lines visually separate independent definitions and make files easier to scan.

**Suggested action:**  

Insert the required blank line.

**Limitations:**  

Compact formatting may be intentional in generated code, small examples, or tightly grouped helper definitions.

```python
def a():
    pass
def b():
    pass
```

---

### STYLE-010: Missing docstring for function

Detects functions without a docstring.

**Why it matters:**  

Docstrings explain purpose, parameters, return values, side effects, and usage constraints.

**Suggested action:**  

Add a concise function docstring.

**Limitations:**  

Docstrings may be unnecessary for simple private helpers, tests, generated code, local nested functions, or functions whose intent is already obvious from their name and usage.

```python
def process_data(data):
    return data.strip()
```

---

### STYLE-011: Missing docstring for class

Detects classes without a docstring.

**Why it matters:**  

Class docstrings explain responsibility, intended usage, and important attributes.

**Suggested action:**  

Add a concise class docstring.

**Limitations:**  

Docstrings may be unnecessary for tiny internal helper classes, test-only classes, generated code, dataclasses with self-explanatory fields, or local classes inside tests.

```python
class UserService:
    pass
```

---

### STYLE-012: Missing docstring for module

Detects modules without a module-level docstring.

**Why it matters:**  

Module docstrings explain the file purpose and help readers understand its role without inspecting every function or class.

**Suggested action:**  

Add a module-level docstring.

**Limitations:**  

Module docstrings may be unnecessary for package markers, tiny scripts, generated files, test modules, examples, or configuration files.

---

## Semantic Rules

Semantic rules identify code patterns that may lead to incorrect behaviour, hidden bugs, or unclear intent.

Unlike style rules, semantic rules focus on suspicious program behaviour rather than formatting. Some rules can be fixed automatically when the transformation is local and semantics-preserving. Others only provide advisory comments because the correct fix depends on developer intent.

---

### SEM-001: Condition is always true

Detects `if` statements whose condition can be determined as always true.

**Why it matters:**  

The conditional branch is redundant and may hide leftover debugging code, obsolete logic, or a missing real condition.

**Suggested action:**  

Remove the redundant condition and keep the body, or replace the constant condition with the intended expression.

**Limitations:**  

Constant conditions may be intentional in generated code, debugging blocks, feature flags, or code used to visually isolate a block.

```python
if 1:
    print("always")
```

---

### SEM-002: While condition is always true

Detects `while` loops whose condition can be determined as always true.

**Why it matters:**  

An always-true loop can become infinite and may block execution or consume resources.

**Suggested action:**  

Add an explicit exit condition or make the break/return mechanism clear.

**Limitations:**  

Infinite loops may be intentional in servers, workers, event loops, REPLs, or loops controlled by external signals.

```python
while True:
    break
```

---

### SEM-003: Comparison to None using == or !=

Detects comparisons to `None` using equality operators.

**Why it matters:**  

`None` is a singleton and should be compared using identity operators. Custom equality logic may make `== None` unreliable or misleading.

**Suggested action:**  

Use `is None` or `is not None`.

**Limitations:**  

Rare false positives may occur in tests that intentionally verify custom equality behaviour.

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

### SEM-004: Assignment in condition

Detects assignments inside `if` or `while` conditions using the walrus operator.

**Why it matters:**  

Combining assignment with control-flow decisions can reduce readability and hide state changes.

**Suggested action:**  

Move the assignment before the condition if clarity improves.

**Limitations:**  

The walrus operator is idiomatic in some simple patterns, such as reading chunks or matching regular expressions.

```python
if (n := get_value()):
    print(n)
```

---

### SEM-005: Redeclared variable in same scope

Detects variables assigned again before the previous value is used.

**Why it matters:**  

The earlier assignment has no observable effect and may indicate a lost value, incomplete refactoring, or accidental overwrite.

**Suggested action:**  

Remove the earlier assignment, use the value before reassignment, or rename variables to clarify intent.

**Limitations:**  

Reassignment may be intentional for staged initialisation, readability, or compatibility with generated/framework code.

```python
count = 1
count = 2
```

---

### SEM-006: Exception bound but not used

Detects `except` clauses that bind the exception object but never use it.

**Why it matters:**  

An unused exception alias may indicate missing logging or incomplete error handling.

**Suggested action:**  

Remove the alias or use it for logging, diagnostics, wrapping, or re-raising.

**Limitations:**  

The alias may be intentionally unused during development. Using `_` is clearer for intentionally ignored values.

```python
try:
    risky()
except ValueError as e:
    print("failed")
```

---

### SEM-007: Bare except clause

Detects bare `except:` handlers.

**Why it matters:**  

A bare handler catches all exceptions, including `KeyboardInterrupt` and `SystemExit`, which can hide errors and interfere with shutdown.

**Suggested action:**  

Catch a specific exception type. If broad handling is required, prefer `except Exception:` and log or handle the exception explicitly.

**Limitations:**  

Broad handlers may be intentional at high-level crash boundaries, cleanup logic, or defensive wrappers.

```python
try:
    risky()
except:
    pass
```

---

### SEM-008: Mutable default argument

Detects mutable default values such as lists, dictionaries, or sets.

**Why it matters:**  

Mutable defaults are shared across function calls and can cause state leakage between independent invocations.

**Suggested action:**  

Use `None` as the default and initialise a new object inside the function.

**Limitations:**  

Shared mutable defaults may be intentional for caching or shared state, but this should be explicit and documented.

```python
def add_item(item, bucket=[]):
    bucket.append(item)
    return bucket
```

---

### SEM-009: Print debug statement

Detects standalone `print()` calls that may represent leftover debugging output.

**Why it matters:**  

Debug prints can pollute runtime output, bypass logging configuration, expose internal values, and make automated output harder to parse.

**Suggested action:**  

Remove temporary prints or replace diagnostics with the `logging` module.

**Limitations:**  

`print()` is valid in CLI tools, examples, scripts, teaching code, tests, and user-facing output.

```python
print("debug:", value)
```

---

## Security and Resource Management Rules

Security rules identify constructs that may lead to vulnerabilities, unsafe execution, or improper resource handling.

These rules are conservative and context-dependent. They highlight potential risks but do not prove the presence of a vulnerability.

---

### SEC-001: Use of eval()/exec()

Detects dynamic code execution using `eval()` or `exec()`.

**Why it matters:**  

Dynamic execution may allow arbitrary code execution if inputs are not trusted.

**Suggested action:**  

Avoid dynamic execution. Use explicit parsing, function dispatch, or safer alternatives such as `ast.literal_eval()`.

**Limitations:**  

Safe usage depends on input control and isolation. Static analysis cannot determine trust boundaries or sandboxing guarantees.

```python
result = eval(user_input)
```

---

### SEC-002: eval() literal parsing

Detects `eval()` calls that appear to parse Python literals.

**Why it matters:**  

Using `eval()` for parsing is unnecessarily dangerous.

**Suggested action:**  

Replace with `ast.literal_eval()` or a dedicated parser (e.g. `json.loads()`).

**Limitations:**  

The rule assumes the input is literal-like. If execution of code is intentional, manual review is required.

```python
data = eval("[1, 2, 3]")
```

---

### SEC-003: Use of os.system()/os.popen()

Detects shell command execution via legacy APIs.

**Why it matters:**  

Shell execution may allow command injection and provides limited control.

**Suggested action:**  

Use `subprocess.run()` with argument lists and explicit error handling.

**Limitations:**  

Some scripts intentionally rely on shell behaviour. Safety depends on input validation.

```python
import os
os.system("rm -rf /tmp/test")
```

---

### SEC-004: Hardcoded secret

Detects potential hardcoded credentials (passwords, tokens, keys).

**Why it matters:**  

Secrets in source code may be exposed via version control or distribution.

**Suggested action:**  

Move secrets to environment variables or secure configuration.

**Limitations:**  

Heuristic-based. May produce false positives for test data, placeholders, or non-sensitive variables.

```python
password = "admin123"
api_key = "secret-key"
```

---

### SEC-005: Insecure randomness

Detects usage of `random` module in security-sensitive contexts.

**Why it matters:**  

`random` is predictable and unsuitable for security purposes.

**Suggested action:**  

Use `secrets` module or cryptographic randomness.

**Limitations:**  

The rule cannot determine whether randomness is used in a security context.

```python
import random
token = str(random.randint(1000, 9999))
```

---

### SEC-006: open() without context manager

Detects file opening without a `with` statement.

**Why it matters:**  

May lead to resource leaks and unclosed file handles.

**Suggested action:**  

Use `with open(...) as f:`.

**Limitations:**  

Valid patterns exist where file ownership is transferred or managed elsewhere.

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

## Performance Rules

Performance rules identify patterns that may lead to unnecessary computation, memory usage, or reduced readability.

These rules are heuristic by nature and do not prove actual performance issues. Their goal is to highlight likely inefficiencies and suggest more idiomatic or efficient alternatives.

---

### PERF-001: Print in list comprehension

Detects list comprehensions used only for side effects (e.g. `print()`).

**Why it matters:**  

List comprehensions are intended to build collections. Using them for side effects reduces readability and creates unnecessary intermediate lists.

**Suggested action:**  

Replace the comprehension with a standard `for` loop.

**Limitations:**  

This rule assumes the list result is unused. If the list is intentionally used, manual review is required.

```python
[print(x) for x in items]
```

---

### PERF-002: Useless list comprehension

Detects list comprehensions whose result is not used.

**Why it matters:**  

Creating a list without using it wastes memory and obscures intent.

**Suggested action:**  

Replace with a `for` loop or use the result explicitly.

**Limitations:**  

Usage may be indirect or not visible to static analysis (e.g. debugging, REPL, framework hooks).

```python
[x for x in items]
```

---

### PERF-003: Redundant sort before min/max

Detects `sorted(... )` passed directly into `min()` or `max()`.

**Why it matters:**  

Sorting is unnecessary when only the minimum or maximum value is needed.

**Suggested action:**  

Call `min()` or `max()` directly on the iterable.

**Limitations:**  

If sorting was intended for reuse or clarity, removing it may not be desirable.

```python
smallest = sorted(values)[0]
```

---

### PERF-004: Unnecessary copy

Detects redundant copying of objects or iterables.

**Why it matters:**  

Unnecessary copies increase memory usage and computation cost.

**Suggested action:**  

Remove the copy when safe.

**Limitations:**  

Copies may be intentional for mutation safety, defensive programming, or API contracts.

```python
items2 = list(items)
```

---

### PERF-005: Nested loops over same collection

Detects nested loops iterating over the same collection.

**Why it matters:**  

May result in quadratic time complexity.

**Suggested action:**  

Consider alternative data structures (set, dict) or a single-pass solution.

**Limitations:**  

Valid for pairwise comparison or when all combinations are required.

```python
for x in items:
    process_a(x)

for x in items:
    process_b(x)
```

---

### PERF-006: Loop could be a comprehension

Detects loops that could be rewritten as comprehensions.

**Why it matters:**  

Comprehensions can be more concise and idiomatic.

**Suggested action:**  

Rewrite only if readability improves.

**Limitations:**  

Comprehensions may reduce clarity in complex logic or debugging scenarios.

```python
result = []
for x in items:
    result.append(x * 2)
```

---

### PERF-007: Use generator in join()

Detects `str.join()` used with a list instead of a generator.

**Why it matters:**  

Avoids creating unnecessary intermediate lists.

**Suggested action:**  

Use a generator expression.

**Limitations:**  

For small inputs, the difference is negligible. Lists may be intentionally reused.

```python
",".join(str(x) for x in items)
```

---

## Dead Code Rules

Dead code rules identify code that does not affect the observable behaviour of the program or cannot be executed.

These rules are generally more actionable than style or complexity rules, and often support safe automatic fixes.

---

### DEAD-001: Unused variable

Detects assignments where the assigned variable is never used.

**Why it matters:**  

Unused variables introduce noise and reduce readability. They may indicate incomplete refactoring, missing logic, or mistakes where computed values are not used.

**Suggested action:**  

Remove the assignment if the value is not needed. If the expression has side effects, keep the expression and remove only the assignment.

**Limitations:**  

This rule may produce false positives when variables are intentionally unused (e.g. debugging, placeholders, underscore variables), or when usage is indirect (e.g. dynamic evaluation, reflection, framework hooks).

```python
x = 10
return 5
```

---

### DEAD-002: Unreachable code

Detects statements that appear after terminal control flow operations such as `return`, `raise`, `break`, or `continue`.

**Why it matters:**  

Unreachable code is never executed and may indicate logical errors or incomplete refactoring. It reduces clarity and can mislead developers about actual behaviour.

**Suggested action:**  

Remove unreachable statements or restructure the control flow to ensure intended logic is executed.

**Limitations:**  

This rule may produce false positives in cases involving conditional compilation patterns, debugging constructs, or code paths that are not statically visible.

```python
def f():
    return 1
    print("never runs")
```

---

### DEAD-003: Unused assignment (keep value)

Detects assignments where the assigned variable is unused but the expression may have side effects.

**Why it matters:**  

Blindly removing such assignments can change program behaviour if the expression performs side effects.

**Suggested action:**  

Replace the assignment with the original expression to preserve side effects, or remove it entirely if the expression is pure.

**Limitations:**  

This rule relies on heuristics and cannot reliably determine whether an expression has side effects. Complex assignments and dynamic behaviour require manual review.

```python
def f():
    x = print("hello")
    return 1
```

---

## Complexity Rules

Complexity rules identify code structures that may reduce readability, maintainability, and ease of testing. These rules are advisory by design, because safe refactoring usually requires developer intent and broader semantic context.

---

### CX-001: Function has too many parameters

Detects functions or methods whose number of parameters exceeds the configured limit.

**Why it matters:**  

Long parameter lists make functions harder to understand, call correctly, test, and maintain. They may also indicate that the function has too many responsibilities or that related values should be grouped into a single object.

**Suggested action:**  

Group related parameters into a dataclass, configuration object, value object, or domain model. If the function mixes multiple responsibilities, split it into smaller functions.

**Limitations:**  

This rule may produce false positives for framework callbacks, generated code, thin wrappers, constructors, or functions that intentionally mirror an external API.

```python
def create_user(name, age, city, email, phone, role, active):
    pass
```

---



### CX-002: Too deep nesting

Detects control-flow structures such as `if`, `for`, `while`, and `try` that are nested deeper than the configured threshold.

**Why it matters:**  

Deep nesting increases cognitive complexity and makes the main execution path harder to follow. It can also make edge cases harder to identify, test, and safely modify.

**Suggested action:**  

Reduce nesting by using guard clauses, early returns, `continue`, helper functions, or simpler conditional structures.

**Limitations:**  

This rule is heuristic. Deep nesting may be acceptable in short, tightly scoped blocks, parsers, state machines, or algorithms where nested structure directly represents the problem being solved.

```python
if a:
    if b:
        if c:
            if d:
                work()
```

---

### CX-003: Too long function

Detects functions or async functions whose relevant statement count exceeds the configured limit.

**Why it matters:**  

Long functions are harder to read, test, and maintain. They often combine multiple responsibilities, making future changes more fragile.

**Suggested action:**  

Extract coherent parts into helper functions, move domain-specific behaviour into dedicated objects, or simplify branching before splitting the function.

**Limitations:**  

This rule may produce false positives for generated code, simple sequential setup code, test cases, data-loading routines, or functions where splitting would reduce clarity instead of improving it.

---

[Back to README](../README.md) | [Previous: Rules](rules.md) | [Next: Rule DSL](rule-dsl.md)