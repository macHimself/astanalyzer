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
