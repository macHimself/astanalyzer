"""
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
"""

import re

import logging
log = logging.getLogger(__name__)


class Predicate:
    """
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
    """

    def __call__(self, actual, node):
        """Evaluate predicate.

        Must return True if condition is satisfied, otherwise False.
        """
        raise NotImplementedError


class ANY(Predicate):
    """
    Predicate that always returns True.

    Useful as a wildcard in Matcher.where(...).

    Example:
        where("name", ANY())
    """

    def __call__(self, actual, node):
        return True


class EXISTS(Predicate):
    """
    True if attribute exists and is non-empty when sized.

    Semantics:
        - actual is not None
        - if object defines __len__, then len(actual) > 0
        - otherwise any non-None value is accepted
    """

    def __call__(self, actual, node):
        if actual is None:
            return False
        if hasattr(actual, "__len__"):
            return len(actual) > 0
        return True


class NONEMPTY(Predicate):
    """
    True if attribute is non-empty.

    Example:
        where("name", NONEMPTY())

    Semantics:
        - None -> False
        - str -> True if stripped string is non-empty
        - collections -> True if len(...) > 0
        - other objects -> True unless length check fails
    """

    def __call__(self, actual, node):
        if actual is None:
            return False
        if isinstance(actual, str):
            return bool(actual.strip())
        try:
            return len(actual) > 0
        except Exception:
            return True


class REGEX(Predicate):
    """
    True if string attribute matches a regular expression.

    Example:
        where("name", REGEX(r"^test_"))

    Semantics:
        - actual must be str
        - True if re.search(...) finds a match
        - otherwise False
    """

    def __init__(self, pattern: str):
        self.rx = re.compile(pattern)

    def __call__(self, actual, node):
        return isinstance(actual, str) and bool(self.rx.search(actual))


class IN_(Predicate):
    """
    True if attribute value is in a given collection.

    Example:
        where("name", IN_(["foo", "bar"]))

    Semantics:
        - actual in values
        - returns False if actual is not present
    """

    def __init__(self, values):
        self.values = set(values)

    def __call__(self, actual, node):
        return actual in self.values


class OP(Predicate):
    """
    Generic comparison predicate.

    Example:
        OP(">", 10)
        OP("==", "foo")

    Supported operators:
        '==', '!=', '>', '>=', '<', '<='

    Semantics:
        - compares actual with provided value
        - returns False if comparison raises an exception
    """

    def __init__(self, op: str, value):
        self.op = op
        self.value = value

    def __call__(self, actual, node):
        try:
            return {
                "==": actual == self.value,
                "!=": actual != self.value,
                ">": actual > self.value,
                ">=": actual >= self.value,
                "<": actual < self.value,
                "<=": actual <= self.value,
            }[self.op]
        except Exception:
            return False


class TYPE(Predicate):
    """
    True if attribute is an AST/astroid node of given type.

    Example:
        where("value", TYPE("Call"))

    Semantics:
        - compares class name of actual to expected type name
        - returns False if actual has no class
    """

    def __init__(self, typename: str):
        self.typename = typename

    def __call__(self, actual, node):
        return getattr(actual, "__class__", None).__name__ == self.typename


class VAL_EQ(Predicate):
    """
    Compare normalized value of AST node to expected literal.
    """

    def __init__(self, value):
        self.value = value

    def __call__(self, actual, node):
        try:
            if actual is None:
                normalized = None
            elif hasattr(actual, "value"):
                normalized = actual.value
            else:
                normalized = actual
            return normalized == self.value
        except Exception:
            return False
        

class NOT(Predicate):
    """
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
    """
    def __init__(self, pred: Predicate):
        self.pred = pred

    def __call__(self, actual, node):
        try:
            return not self.pred(actual, node)
        except Exception as e:
            log.debug("Predicate NOT failed: %s", e)
            return False        


def arg_count_gt(
    limit: int,
    *,
    include_posonly: bool = True,
    include_args: bool = True,
    include_kwonly: bool = False,
    include_vararg: bool = False,
    include_kwarg: bool = False,
):
    """
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
    """
    def _predicate(node):
        args_obj = getattr(node, "args", None)
        if args_obj is None:
            return False

        cnt = 0

        if include_posonly:
            posonly = getattr(args_obj, "posonlyargs", None)
            if isinstance(posonly, list):
                cnt += len(posonly)

        if include_args:
            a = getattr(args_obj, "args", None)
            if isinstance(a, list):
                cnt += len(a)

        if include_kwonly:
            kwa = getattr(args_obj, "kwonlyargs", None)
            if isinstance(kwa, list):
                cnt += len(kwa)

        if include_vararg:
            if getattr(args_obj, "vararg", None) is not None:
                cnt += 1

        if include_kwarg:
            if getattr(args_obj, "kwarg", None) is not None:
                cnt += 1

        return cnt > limit

    return _predicate


def parent_depth_at_least(types, min_depth: int):
    """
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
    """
    if isinstance(types, str):
        if "|" in types:
            allowed = {t.strip() for t in types.split("|") if t.strip()}
        else:
            allowed = {types}
    else:
        allowed = set(types)

    def _predicate(node):
        depth = 0
        p = getattr(node, "parent", None)
        while p is not None:
            if p.__class__.__name__ in allowed:
                depth += 1
            p = getattr(p, "parent", None)
        return depth >= min_depth

    return _predicate
