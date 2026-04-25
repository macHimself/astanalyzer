[Back to README](../README.md) | [Previous: Fixes](fixes.md) | [Next: Custom Rules](custom-rules.md)

# Fixer Actions

Fixer actions describe proposed source-code changes.

They are collected by the fixer DSL and later converted into reviewable fix proposals and patch previews.

---

## Insert actions

### `insert_before(text)`

Inserts text before the matched node or line.

```python
fix().insert_before("x = 1")
```

---

### `insert_after(text)`

Inserts text after the matched node or line.

```python
fix().insert_after("return x")
```

---

### `insert_at_body_start(text)`

Inserts text at the beginning of a function, class, or block body.

```python
fix().insert_at_body_start("result = []")
```

---

### `prepend(text)`

Prepends text to the target file or target region.

```python
fix().prepend("import os")
```

---

### `append(text)`

Appends text to the target file or target region.

```python
fix().append("return result")
```

---

## Replace actions

### `replace_with(text)`

Replaces the matched node or target region with text.

```python
fix().replace_with("pass")
```

---

### `replace_line(text)`

Replaces the full source line.

```python
fix().replace_line("return value")
```

---

### `replace_node_text(text)`

Replaces the textual representation of the matched node.

```python
fix().replace_node_text("None")
```

---

### `replace_range(text)`

Replaces a computed source range.

```python
fix().replace_range("x is None")
```

---

### `replace_with_value()`

Replaces the target with its value expression.

```python
fix().replace_with_value()
```

---

## Remove actions

### `remove_line()`

Removes the source line containing the matched node.

```python
fix().remove_line()
```

---

### `delete_node()`

Deletes the matched AST node.

```python
fix().delete_node()
```

---

### `remove_statement()`

Removes the whole statement containing the matched node.

```python
fix().remove_statement()
```

---

### `remove_dead_code_after()`

Removes unreachable code after a terminal statement.

```python
fix().remove_dead_code_after()
```

---

### `remove_node(ref=...)`

Removes a previously captured node.

```python
fix().remove_node(ref="previous_assign")
```

---

## Comment and documentation actions

### `comment_before(text)`

Adds a comment before the matched node.

```python
fix().comment_before("TODO: review this")
```

---

### `comment_after(text)`

Adds a comment after the matched node.

```python
fix().comment_after("Consider refactoring")
```

---

### `comment_on_function(text)`

Adds a comment near a function definition.

```python
fix().comment_on_function("TODO: simplify branching")
```

---

### `add_docstring(text)`

Adds a docstring to a function or class.

```python
fix().add_docstring('"""TODO: Add docstring."""')
```

---

### `add_module_docstring(text)`

Adds a module-level docstring.

```python
fix().add_module_docstring('"""TODO: Add module docstring."""')
```

---

## Formatting actions

### `strip_trailing_whitespace()`

Removes trailing whitespace.

```python
fix().strip_trailing_whitespace()
```

---

### `insert_blank_line_before()`

Inserts a blank line before the matched node.

```python
fix().insert_blank_line_before()
```

---

## Block restructuring actions

### `remove_block_header(...)`

Removes a block header such as an `else`.

```python
fix().remove_block_header("orelse")
```

---

### `unindent_block(...)`

Unindents a block after removing its header.

```python
fix().unindent_block("orelse", spaces=4)
```

---

### `remove_orelse_header()`

Removes an `else` header.

```python
fix().remove_orelse_header()
```

---

### `unindent_orelse()`

Unindents the `else` body.

```python
fix().unindent_orelse()
```

---

### `flatten_always_true_if()`

Flattens an always-true `if` block.

```python
fix().flatten_always_true_if()
```

---

## Semantic fix actions

### `replace_none_comparison_operator()`

Replaces `== None` / `!= None` with `is None` / `is not None`.

```python
fix().replace_none_comparison_operator()
```

---

### `remove_except_alias()`

Removes an unused exception alias.

```python
fix().remove_except_alias()
```

---

### `replace_bare_except_with_exception()`

Replaces bare `except:` with `except Exception:`.

```python
fix().replace_bare_except_with_exception()
```

---

### `replace_mutable_default_with_none()`

Replaces mutable default arguments with `None`.

```python
fix().replace_mutable_default_with_none()
```

Usually used together with:

```python
fix().insert_mutable_default_guard()
```

---

### `insert_mutable_default_guard()`

Adds an initialization guard for mutable defaults.

```python
fix().insert_mutable_default_guard()
```

---

## Performance fix actions

### `replace_print_listcomp_with_for_loop()`

Replaces list comprehension used only for `print()` side effects with a loop.

```python
fix().replace_print_listcomp_with_for_loop()
```

---

### `remove_redundant_sorted()`

Removes unnecessary `sorted(...)` before min/max-like access.

```python
fix().remove_redundant_sorted()
```

---

### `replace_unnecessary_copy()`

Removes unnecessary copying.

```python
fix().replace_unnecessary_copy()
```

---

### `replace_join_listcomp_with_generator()`

Replaces list comprehension inside `join()` with a generator expression.

```python
fix().replace_join_listcomp_with_generator()
```

---

## Security fix actions

### `replace_eval_with_literal_eval()`

Replaces `eval(...)` used for literal parsing with `ast.literal_eval(...)`.

```python
fix().replace_eval_with_literal_eval()
```

Usually combined with:

```python
fix().ensure_import("ast")
```

---

### `replace_os_system_with_subprocess_run()`

Replaces `os.system(...)` with `subprocess.run(...)`.

```python
fix().replace_os_system_with_subprocess_run()
```

Usually combined with:

```python
fix().ensure_import("subprocess")
```

---

### `ensure_import(module)`

Ensures that a module import exists.

```python
fix().ensure_import("subprocess")
```

---

## Custom actions

### `custom(callback, **options)`

Registers a custom fixer action.

```python
fix().custom(my_callback, option="value")
```

Use custom actions only when the built-in fixer DSL cannot express the intended transformation.

---

## Reasons

Every fixer should explain why the change is proposed.

```python
fix()
    .replace_none_comparison_operator()
    .because("Use 'is' or 'is not' when comparing with None.")
```

## Notes

- Fixer actions are collected as proposals, not applied immediately.
- Most actions are line-based.
- Some actions operate on the whole file.
- Generated changes should be reviewed before applying.
- Patch previews make proposed changes visible before application.

---

[Back to README](../README.md) | [Previous: Fixes](fixes.md) | [Next: Custom Rules](custom-rules.md)