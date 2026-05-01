[Back to Matcher Helpers](../matcher-helpers.md) | [Back to Rule DSL](../rule-dsl.md) | [Back to README](../../README.md)

# Tools Reference

> This file is generated automatically. Do not edit it manually.

## `is_snake`

**Type:** function

```python
is_snake(name)
```

Return True if `name` follows snake_case convention.

---

## `is_pascal`

**Type:** function

```python
is_pascal(name)
```

Return True if `name` follows PascalCase convention.

---

## `split_identifier_parts`

**Type:** function

```python
split_identifier_parts(name)
```

Split identifier into semantic parts using underscores and camel-case boundaries.

Examples:
    api_key -> ["api", "key"]
    apiKey -> ["api", "key"]
    accessToken -> ["access", "token"]
    monkey -> ["monkey"]

---

## `is_local_function_assignment`

**Type:** function

```python
is_local_function_assignment(node)
```

Return True if the assignment is inside a function-like local scope.

Dead-code heuristics for assignments are reliable mainly for local variables,
not for module-level or class-level declarations that may be used elsewhere.

---

## `is_unused_assign`

**Type:** function

```python
is_unused_assign(node)
```

Return True if assigned names are not read before being overwritten
or before the relevant control-flow scope ends.

Heuristic only. Handles:
- simple reassignment flows: x = x.strip()
- unpacking assignments
- reads in conditions before branch-local reassignment
- values assigned in branches and used after branch merge
- values assigned in nested blocks and used after outer block completion
- loop-carried state updates in for/while loops

---

## `get_enclosing_scope`

**Type:** function

```python
get_enclosing_scope(node)
```

Return the nearest enclosing lexical scope node.

---

## `is_name_shadowed_in_scope`

**Type:** function

```python
is_name_shadowed_in_scope(node, name)
```

Return True if `name` is defined in the enclosing lexical scope.

---

## `is_name_rebound_in_scope`

**Type:** function

```python
is_name_rebound_in_scope(node, name)
```

Return True if `name` is rebound in the enclosing lexical scope in a way that
should suppress builtin/module-name based security heuristics.

Unlike `is_name_shadowed_in_scope`, this intentionally ignores imports such as
`import os` or `import random`, because those are the normal, desired uses
for rules that target module-qualified calls.

---

## `is_noop_stmt`

**Type:** function

```python
is_noop_stmt(stmt)
```

Return True if the statement is effectively a no-op.

---

## `is_empty_seq`

**Type:** function

```python
is_empty_seq(seq)
```

Return True if the sequence is empty or contains only no-op statements.

---

## `iter_relevant_bodies`

**Type:** function

```python
iter_relevant_bodies(node)
```

Yield named statement bodies relevant for empty-block analysis.

Examples include `body`, `orelse`, exception handler bodies, and `finalbody`.

---

## `iter_required_bodies`

**Type:** function

```python
iter_required_bodies(node)
```

Yield only block bodies whose emptiness should count as an empty block.

This excludes optional parts such as `try.finalbody`, which may be absent
without making the overall block empty.

---

## `is_empty_block`

**Type:** function

```python
is_empty_block(node)
```

Return True if any required body of the node is empty or contains only no-op statements.

---

## `empty_parts`

**Type:** function

```python
empty_parts(node)
```

Return names of required block parts that are empty or contain only no-op statements.

---

## `is_terminal_stmt`

**Type:** function

```python
is_terminal_stmt(stmt)
```

Return True if the statement terminates local control flow.

---

## `body_ends_terminal`

**Type:** function

```python
body_ends_terminal(seq)
```

Return True if the last statement in the sequence is terminal.

---

## `has_redundant_else_after_terminal`

**Type:** function

```python
has_redundant_else_after_terminal(node)
```

Return True if an if/elif/else chain contains an unnecessary else branch
after a terminal statement.

---

## `count_returns_in_function`

**Type:** function

```python
count_returns_in_function(node, stop_after)
```

Count return statements inside a function while ignoring nested scopes.

Nested functions and classes are not traversed.

---

## `has_multiple_returns`

**Type:** function

```python
has_multiple_returns(node)
```

Return True if the function contains at least two return statements.

---

## `get_file_content_from_node`

**Type:** function

```python
get_file_content_from_node(node)
```

Return cached source file content from the node root, if available.

---

## `long_line_numbers`

**Type:** function

```python
long_line_numbers(node, max_len)
```

Return source line numbers whose length exceeds the given limit.

---

## `has_long_lines`

**Type:** function

```python
has_long_lines(node, max_len)
```

Return True if the source file contains any line longer than the given limit.

---

## `is_module_constant`

**Type:** function

```python
is_module_constant(node)
```

Return True if the node represents a simple module-level constant assignment.

Dunder names are excluded.

---

## `trailing_whitespace_line_numbers`

**Type:** function

```python
trailing_whitespace_line_numbers(content)
```

Return trailing-whitespace line numbers outside multiline string literals.

---

## `has_trailing_whitespace`

**Type:** function

```python
has_trailing_whitespace(module_node)
```

No documentation available.

---

## `trailing_whitespace_comment`

**Type:** function

```python
trailing_whitespace_comment(module_node)
```

No documentation available.

---

## `strip_trailing_whitespace`

**Type:** function

```python
strip_trailing_whitespace(module_node, suggestion_lines, context)
```

No documentation available.

---

## `missing_blank_before_def`

**Type:** function

```python
missing_blank_before_def(node)
```

Return True if the definition is missing the required blank lines before it.

---

## `missing_blank_before_def_comment`

**Type:** function

```python
missing_blank_before_def_comment(node)
```

Return an explanatory comment for a missing blank line before a definition.

---

## `insert_function_docstring`

**Type:** function

```python
insert_function_docstring(node, suggestion_lines, context)
```

Insert a generated docstring into a function definition suggestion.

---

## `insert_class_docstring`

**Type:** function

```python
insert_class_docstring(node, suggestion_lines, context)
```

Insert a generated docstring into a class definition suggestion.

---

## `function_arg_count`

**Type:** function

```python
function_arg_count(node, ignore_bound_first_arg, ignore_init)
```

Return the number of relevant function arguments for complexity checks.

---

## `arg_count_gt`

**Type:** function

```python
arg_count_gt(limit, ignore_bound_first_arg, ignore_init)
```

Build a predicate that matches functions with more than `limit` relevant arguments.

---

## `parent_depth_at_least`

**Type:** function

```python
parent_depth_at_least(type_names, min_depth)
```

Build a predicate that matches nodes nested inside the given parent types
at least `min_depth` times.

---

## `count_relevant_statements`

**Type:** function

```python
count_relevant_statements(node)
```

Count executable statements in a function while ignoring no-op string
expressions and nested function/class scopes.

---

## `loop_comprehension_suggestion`

**Type:** function

```python
loop_comprehension_suggestion(for_node)
```

Suggest a list, set, or dict comprehension replacement for a simple loop.

Returns:
    tuple[str | None, str | None]:
        Pair of (kind, suggestion), or (None, None) if no safe rewrite pattern is found.

---

## `is_loop_comprehension_candidate`

**Type:** function

```python
is_loop_comprehension_candidate(for_node)
```

Return True if the loop can be rewritten as a comprehension.

---

## `is_nested_loop_same_stable_collection`

**Type:** function

```python
is_nested_loop_same_stable_collection(node)
```

Return True when an inner loop iterates over the same stable collection
as an enclosing outer loop.

---

## `is_builtin_name_call`

**Type:** function

```python
is_builtin_name_call(node, allowed_names)
```

Return True if node is a call to a non-shadowed builtin name.

---

## `is_builtin_print_call`

**Type:** function

```python
is_builtin_print_call(node)
```

Return True if node is a call to builtin print().

---

## `is_redundant_sorted_before_minmax`

**Type:** function

```python
is_redundant_sorted_before_minmax(node)
```

Return True for min(sorted(x)) / max(sorted(x)) with non-shadowed builtins.

---

## `is_probably_str_join_call`

**Type:** function

```python
is_probably_str_join_call(node)
```

Return True for calls of the form '<string-literal>.join(...)'.

---

## `is_builtin_eval_or_exec_call`

**Type:** function

```python
is_builtin_eval_or_exec_call(node)
```

Return True if node is a call to non-shadowed builtin eval() or exec().

---

## `is_explicit_builtins_eval_or_exec_call`

**Type:** function

```python
is_explicit_builtins_eval_or_exec_call(node)
```

Return True for calls like builtins.eval(...) or builtins.exec(...).

---

## `is_builtin_eval_literal_candidate`

**Type:** function

```python
is_builtin_eval_literal_candidate(node)
```

Return True for non-shadowed eval('<literal-like>') candidates.

---

## `is_builtin_os_system_or_popen_call`

**Type:** function

```python
is_builtin_os_system_or_popen_call(node)
```

Return True for calls like os.system(...) or os.popen(...), excluding local rebinding of `os`.

---

## `is_probable_secret_target_name`

**Type:** function

```python
is_probable_secret_target_name(name, suspect_names)
```

Return True if identifier contains a secret-like semantic part.

---

## `is_hardcoded_secret_assignment`

**Type:** function

```python
is_hardcoded_secret_assignment(node, suspect_names)
```

Return True for assignments of non-empty string literals to secret-like names.

---

## `is_insecure_random_call`

**Type:** function

```python
is_insecure_random_call(node, unsafe_funcs)
```

Return True for calls like random.choice(...), excluding local rebinding of `random`.

---

## `is_builtin_open_call`

**Type:** function

```python
is_builtin_open_call(node)
```

Return True if node is a call to non-shadowed builtin open().

---


[Back to Matcher Helpers](../matcher-helpers.md) | [Back to Rule DSL](../rule-dsl.md) | [Back to README](../../README.md)