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
