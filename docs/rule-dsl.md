[Back to README](../README.md) | [Previous: Rule Catalog](rule-catalog.md) | [Next: Matcher Helpers](matcher-helpers.md)

# Rule DSL

The Rule DSL (matcher) describes AST patterns declaratively.

---

## Basic usage

```python
match("FunctionDef")
match("If|For|While")
```

---

## Core methods

### Structure

```python
match("FunctionDef").has("Return")
match("FunctionDef").missing("Return")
match("FunctionDef").with_child(match("Return"))
```

---

### Attributes

```python
match("FunctionDef").where("name", "foo")
match("FunctionDef").where_regex("name", r"^[a-z_]+$")
match("FunctionDef").where_len("args.args", 2)
```

---

### Calls

```python
match("Call").where_call(name="print")
match("Call").where_call(qual="os.system")
```

---

### Relations

```python
match("Call").has_parent("Expr")
match("FunctionDef").with_descendant(match("Call"))
```

---

### Sequences

```python
match("Assign").next_sibling(match("Assign"))
match("Assign").later_in_block(match("Expr"))
```

---

### Logic

```python
match("FunctionDef").and_(...)
match("ClassDef").or_(...)
match("FunctionDef").not_()
```

---

## Custom predicates

```python
def is_large(node):
    return len(node.body) > 10

match("FunctionDef").satisfies(is_large)
```

---

## Helper methods

```python
match("FunctionDef").missing_docstring()
match("Assign").is_unused()
match("FunctionDef").multiple_returns()
match("If").redundant_else_after_terminal()
```

---

## Notes

- matchers operate on astroid nodes
- prefer declarative conditions over custom predicates
- keep matchers simple and composable

---

[Back to README](../README.md) | [Previous: Rule Catalog](rule-catalog.md) | [Next: Matcher Helpers](matcher-helpers.md)