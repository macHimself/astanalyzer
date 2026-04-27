[Back to README](../README.md) | [Previous: Custom Rules](custom-rules.md) | [Next: Limitations](limitations.md)

# Ignoring Findings

AstAnalyzer allows suppressing findings directly in code using inline comments.

Use this only when the code is intentional and acceptable.

Ignore directives are preserved in the source code and will suppress findings in future scans.

## Ignore next node

Suppress a rule for the following statement:

```python
# astanalyzer: ignore-next STYLE-003
def foo():
    ...
```

## Ignore on the same line

```python
x = eval(data)  # astanalyzer: ignore SEC-030
```

## Ignore multiple rules

```python
# astanalyzer: ignore-next STYLE-003, FUNC-001
def foo():
    ...
```

## Disable rules in a block

```python
# astanalyzer: disable STYLE-003

def foo():
    ...

# astanalyzer: enable STYLE-003
```

## Ignore all rules

```python
# astanalyzer: ignore-next
def foo():
    ...
```

---

[Back to README](../README.md) | [Previous: Custom Rules](custom-rules.md) | [Next: Limitations](limitations.md)