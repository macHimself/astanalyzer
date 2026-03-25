"""
Predicate DSL used by Matcher.where(...).

This module defines reusable predicate objects that can be passed as
`expected` values to Matcher.where(...) conditions.

Each Predicate implements:

    __call__(actual, node) -> bool

Where:
    actual: The resolved attribute value from the matched node
    node:   The full AST/astroid node currently being evaluated

Predicates must be side-effect free and exception-safe.
Any exception during evaluation should result in False.
"""

import re

import logging
log = logging.getLogger(__name__)


class Predicate:
    """Base class for attribute comparison predicates.

    Subclasses must implement:

        __call__(actual, node) -> bool

    Where:
        actual: value extracted from node via Matcher._get_attr(...)
        node:   full node object (astroid or ast)

    Predicates may ignore `node` if not needed.
    """

    def __call__(self, actual, node):
        """Evaluate predicate.

        Must return True if condition is satisfied, otherwise False.
        """
        raise NotImplementedError


class ANY(Predicate):
    """Predicate that always returns True.

    Useful as a wildcard in Matcher.where(...).
    """

    def __call__(self, actual, node):
        return True


class EXISTS(Predicate):
    """True if attribute exists and is not empty (when sized).

    Semantics:
        - actual is not None
        - if object has __len__, then len(actual) must be > 0
        - otherwise any non-None object is accepted

    Notes:
        This does not trim strings (see NONEMPTY for stricter behaviour).
    """

    def __call__(self, actual, node):
        return actual is not None and (
            len(actual) if hasattr(actual, "__len__") else True
        )


class NONEMPTY(Predicate):
    """True if attribute is non-empty.

    Semantics:
        - None -> False
        - str -> True if stripped string is non-empty
        - collections -> True if len(...) > 0
        - other objects -> True unless len(...) raises

    Notes:
        More strict than EXISTS for strings.
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
    """True if string attribute matches given regular expression.

    Args:
        pattern: Regular expression pattern (compiled with re.compile).

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
    """True if attribute value is in a given collection.

    Args:
        values: Iterable of allowed values (converted to set internally).

    Semantics:
        - actual in values
        - False if actual is not hashable or not present
    """

    def __init__(self, values):
        self.values = set(values)

    def __call__(self, actual, node):
        return actual in self.values


class OP(Predicate):
    """Generic comparison predicate.

    Example:
        OP('>', 10)
        OP('==', 'foo')

    Supported operators:
        '==', '!=', '>', '>=', '<', '<='

    Semantics:
        - Attempts comparison between `actual` and `self.value`
        - Returns False on any exception (TypeError, KeyError, etc.)
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
    """True if attribute is an AST/astroid node of given class name.

    Args:
        typename: Class name string (e.g., "Name", "Call").

    Semantics:
        - getattr(actual, "__class__").__name__ must equal typename
        - Returns False if actual has no __class__
    """

    def __init__(self, typename: str):
        self.typename = typename

    def __call__(self, actual, node):
        return getattr(actual, "__class__", None).__name__ == self.typename


class VAL_EQ(Predicate):
    """Compare normalized value of AST node to expected literal.

    This predicate uses Matcher._value_of(...) to extract a comparable
    Python value from astroid/builtin AST nodes.

    Examples:
        VAL_EQ(42)
        VAL_EQ("foo")

    Semantics:
        - Extract normalized value via `_value_of(actual)`
        - Compare equality to provided value
        - Returns False on mismatch
    """

    def __init__(self, value):
        self.value = value

    def __call__(self, actual, node):
        from .matcher import _value_of
        return _value_of(actual) == self.value
    

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
    Build a safe predicate that matches function-like nodes whose argument count
    is greater than `limit`.

    Designed for astroid nodes (FunctionDef/Lambda), but written defensively:
    missing attributes result in False rather than exceptions.

    Parameters
    ----------
    limit:
        The threshold; predicate returns True if arg_count > limit.
    include_posonly:
        Count positional-only args when available (py3.8+ style).
    include_args:
        Count regular positional args (node.args.args).
    include_kwonly:
        Count keyword-only args (node.args.kwonlyargs).
    include_vararg:
        Count vararg (*args) as 1 if present.
    include_kwarg:
        Count kwarg (**kwargs) as 1 if present.

    Returns
    -------
    Callable[[Any], bool]
        A predicate suitable for `where("__custom_condition__", predicate)`.
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
    Build a predicate that checks whether a node is nested inside
    ancestors of given types at least `min_depth` times.

    Parameters
    ----------
    types : str | Iterable[str]
        Node type name(s). Can be:
          - single string: "If"
          - pipe string: "If|For|While"
          - iterable of strings: ("If", "For")
    min_depth : int
        Minimum required nesting depth.

    Returns
    -------
    Callable[[Any], bool]
        Predicate suitable for use with
        where("__custom_condition__", ...).
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


class NOT(Predicate):
    def __init__(self, pred: Predicate):
        self.pred = pred

    def __call__(self, actual, node):
        try:
            return not self.pred(actual, node)
        except Exception:
            return False
        

