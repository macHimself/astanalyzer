[Back to Rule DSL](rule-dsl.md) | [Back to README](../../README.md)

# Matcher Helpers

Matcher helpers are convenience methods built on top of the core matcher DSL.

They are intended for common static-analysis patterns that would otherwise require repetitive AST checks.

---

## Documentation and naming

### `missing_docstring()`

Detects functions without a docstring.

```python
match("FunctionDef").missing_docstring()
```

Use for rules such as missing function documentation.

---

### `missing_module_docstring()`

Detects modules without a module-level docstring.

```python
match("Module").missing_module_docstring()
```

---

### `name_not_snake()`

Detects function names that do not follow snake_case.

```python
match("FunctionDef").name_not_snake()
```

---

### `name_not_pascal()`

Detects class names that do not follow PascalCase.

```python
match("ClassDef").name_not_pascal()
```

---

### `constant_name_not_upper()`

Detects constants that do not follow UPPER_SNAKE_CASE.

```python
match("Assign|AnnAssign").constant_name_not_upper()
```

---

## Structure and complexity

### `multiple_returns()`

Detects functions with multiple return statements.

```python
match("FunctionDef").multiple_returns()
```

---

### `redundant_else_after_terminal()`

Detects redundant `else` blocks after terminal statements such as `return`.

```python
match("If").redundant_else_after_terminal()
```

---

### `empty_block()`

Detects blocks that are syntactically present but effectively empty.

```python
match("If|For|While|FunctionDef|ClassDef").empty_block()
```

---

### `line_too_long(max_length)`

Detects lines exceeding the configured maximum length.

```python
match("Module").line_too_long(100)
```

---

## Semantic checks

### `where_compare_pairwise(...)`

Detects comparisons matching specific operators and values.

```python
match("Compare").where_compare_pairwise(
    op_in=("Eq", "NotEq"),
    any_side_value=None,
)
```

Useful for detecting comparisons such as:

```python
if value == None:
    pass
```

---

### `where_contains(type_name, in_=...)`

Detects whether a specific AST node type appears inside a selected attribute or subtree.

```python
match("If|While").where_contains("NamedExpr", in_="test")
```

Useful for finding assignment expressions inside conditions.

---

### `where_mutable_default_argument()`

Detects mutable default arguments.

```python
match("FunctionDef").where_mutable_default_argument()
```

Example:

```python
def add(item, bucket=[]):
    bucket.append(item)
```

---

## Security-oriented helpers

### `where_target_contains_any(...)`

Detects assignments whose target name contains sensitive words.

```python
match("Assign|AnnAssign").where_target_contains_any(
    "password",
    "token",
    "secret",
)
```

---

### `where_value_is_string_literal(...)`

Detects string literal values.

```python
match("Assign|AnnAssign").where_value_is_string_literal(non_empty=True)
```

Useful together with `where_target_contains_any(...)` for hardcoded secret detection.

---

## Exception handling helpers

### `where_except_binds_name(...)`

Detects exception handlers that bind the exception to a name.

```python
match("ExceptHandler").where_except_binds_name(ignore="_")
```

---

### `where_body_missing_name(...)`

Detects whether the exception variable is unused inside the handler body.

```python
match("ExceptHandler").where_body_missing_name("e")
```

---

## Dead-code helpers

### `is_unused()`

Detects unused assignments or variables, depending on node type and context.

```python
match("Assign").is_unused()
```

---

## Reference

For lower-level helper APIs used by custom matcher rules, see:

- Internals:
  - [Predicates Reference](reference/predicates.md) — reusable conditions for `Matcher.where(...)`
  - [Tools Reference](reference/tools.md) — helper functions for analysing AST nodes and relationships

---

## Notes

- Helpers should remain readable and focused.
- Prefer helper methods when they express intent better than raw AST checks.
- Prefer core matcher chains when the condition is simple.
- Use custom predicates only when the DSL cannot express the condition clearly.

---

[Back to Rule DSL](rule-dsl.md) | [Back to README](../../README.md)