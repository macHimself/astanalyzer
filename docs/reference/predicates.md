[Back to Matcher Helpers](../matcher-helpers.md) | [Back to Rule DSL](../rule-dsl.md) | [Back to README](../../README.md)

# Predicates Reference

> This file is generated automatically. Do not edit it manually.

## `Predicate`

**Type:** class

```python
Predicate
```

Predicate DSL used by Matcher.where(...).

This module defines reusable predicate objects that can be passed as
`expected` values to Matcher.where(...) conditions.

Predicates encapsulate reusable comparison logic and allow expressive,
composable conditions in matcher definitions.

Each Predicate implements:

    __call__(actual, node) -> bool

Where:
    actual: value resolved from the node attribute
    node:   the full AST/astroid node being evaluated

Predicates must be side-effect free and exception-safe.
Any exception during evaluation must result in False.

---

## `ANY`

**Type:** class

```python
ANY
```

Predicate that always returns True.

Useful as a wildcard in Matcher.where(...).

Example:
    where("name", ANY())

---

## `EXISTS`

**Type:** class

```python
EXISTS
```

True if attribute exists and is non-empty when sized.

Semantics:
    - actual is not None
    - if object defines __len__, then len(actual) > 0
    - otherwise any non-None value is accepted

---

## `NONEMPTY`

**Type:** class

```python
NONEMPTY
```

True if attribute is non-empty.

Example:
    where("name", NONEMPTY())

Semantics:
    - None -> False
    - str -> True if stripped string is non-empty
    - collections -> True if len(...) > 0
    - other objects -> True unless length check fails

---

## `REGEX`

**Type:** class

```python
REGEX
```

True if string attribute matches a regular expression.

Example:
    where("name", REGEX(r"^test_"))

Semantics:
    - actual must be str
    - True if re.search(...) finds a match
    - otherwise False

---

## `IN_`

**Type:** class

```python
IN_
```

True if attribute value is in a given collection.

Example:
    where("name", IN_(["foo", "bar"]))

Semantics:
    - actual in values
    - returns False if actual is not present

---

## `OP`

**Type:** class

```python
OP
```

Generic comparison predicate.

Example:
    OP(">", 10)
    OP("==", "foo")

Supported operators:
    '==', '!=', '>', '>=', '<', '<='

Semantics:
    - compares actual with provided value
    - returns False if comparison raises an exception

---

## `TYPE`

**Type:** class

```python
TYPE
```

True if attribute is an AST/astroid node of given type.

Example:
    where("value", TYPE("Call"))

Semantics:
    - compares class name of actual to expected type name
    - returns False if actual has no class

---

## `VAL_EQ`

**Type:** class

```python
VAL_EQ
```

Compare normalized value of AST node to expected literal.

---

## `NOT`

**Type:** class

```python
NOT
```

Negation predicate.

Wraps another predicate and inverts its result.

This allows composition of predicate logic inside Matcher.where(...)
without modifying the original predicate.

Example:
    where("name", NOT(REGEX(r"^test_")))

Semantics:
    - Returns the logical negation of the wrapped predicate
    - Returns False if the wrapped predicate raises an exception

Args:
    pred (Predicate): Predicate to negate.

---

## `arg_count_gt`

**Type:** function

```python
arg_count_gt(limit, include_posonly, include_args, include_kwonly, include_vararg, include_kwarg)
```

Build a predicate that matches functions with more than `limit` arguments.

Example:
    where("__custom_condition__", arg_count_gt(3))

Semantics:
    - counts selected argument kinds on function-like nodes
    - returns True if total count > limit
    - returns False if node has no arguments or structure is missing

Notes:
    - supports fine-grained control over which argument types are counted
    - safe for incomplete or non-function nodes (no exceptions raised)

---

## `parent_depth_at_least`

**Type:** function

```python
parent_depth_at_least(types, min_depth)
```

Build a predicate that matches nodes nested inside specific parent types.

Example:
    where("__custom_condition__", parent_depth_at_least("If", 2))
    where("__custom_condition__", parent_depth_at_least("If|For", 1))

Semantics:
    - walks up the parent chain
    - counts how many ancestors match given types
    - returns True if depth >= min_depth

Args:
    types:
        Node type(s) to match. Can be:
            - single string ("If")
            - union string ("If|For|While")
            - iterable of strings
    min_depth:
        Minimum required nesting depth

---


[Back to Matcher Helpers](../matcher-helpers.md) | [Back to Rule DSL](../rule-dsl.md) | [Back to README](../../README.md)