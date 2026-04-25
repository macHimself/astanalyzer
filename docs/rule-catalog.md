[Back to README](../README.md) | [Previous: Rules](rules.md) | [Next: Rule DSL](rule-dsl.md)

# Rule Catalog

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

[Back to README](../README.md) | [Previous: Rules](rules.md) | [Next: Rule DSL](rule-dsl.md)