import pytest

from astanalyzer.predicates import (
    ANY,
    EXISTS,
    NONEMPTY,
    REGEX,
    IN_,
    OP,
    TYPE,
    VAL_EQ,
    NOT,
    arg_count_gt,
    parent_depth_at_least,
)


class DummyNode:
    pass


class Foo:
    pass


class Bar:
    pass


def test_any_always_returns_true():
    pred = ANY()
    assert pred(None, None) is True
    assert pred("", DummyNode()) is True
    assert pred(123, object()) is True


@pytest.mark.parametrize(
    "actual, expected",
    [
        (None, False),
        ("", False),
        ("x", True),
        ([], False),
        ([1], True),
    ],
)
def test_exists(actual, expected):
    pred = EXISTS()
    assert bool(pred(actual, None)) == expected


def test_exists_returns_true_for_non_none_object_without_len():
    pred = EXISTS()

    class NoLen:
        pass

    assert pred(NoLen(), None) is True


@pytest.mark.parametrize(
    "actual, expected",
    [
        (None, False),
        ("", False),
        ("   ", False),
        ("abc", True),
        ([], False),
        ([1], True),
        ({}, False),
        ({"a": 1}, True),
    ],
)
def test_nonempty(actual, expected):
    pred = NONEMPTY()
    assert pred(actual, None) is expected


def test_nonempty_returns_true_for_object_without_len():
    pred = NONEMPTY()

    class NoLen:
        pass

    assert pred(NoLen(), None) is True


def test_nonempty_returns_true_when_len_raises():
    pred = NONEMPTY()

    class BrokenLen:
        def __len__(self):
            raise RuntimeError("broken")

    assert pred(BrokenLen(), None) is True


def test_regex_matches_string():
    pred = REGEX(r"^test_")
    assert pred("test_name", None) is True


def test_regex_returns_false_for_non_matching_string():
    pred = REGEX(r"^test_")
    assert pred("name", None) is False


def test_regex_returns_false_for_non_string():
    pred = REGEX(r"^test_")
    assert pred(123, None) is False


def test_in_predicate_true_when_value_present():
    pred = IN_(["foo", "bar"])
    assert pred("foo", None) is True


def test_in_predicate_false_when_value_missing():
    pred = IN_(["foo", "bar"])
    assert pred("baz", None) is False


@pytest.mark.parametrize(
    "op, actual, value, expected",
    [
        ("==", 5, 5, True),
        ("!=", 5, 3, True),
        (">", 5, 3, True),
        (">=", 5, 5, True),
        ("<", 3, 5, True),
        ("<=", 5, 5, True),
    ],
)
def test_op_supported_operators(op, actual, value, expected):
    pred = OP(op, value)
    assert pred(actual, None) is expected


def test_op_returns_false_when_comparison_raises():
    pred = OP(">", "x")
    assert pred(5, None) is False


def test_op_returns_false_for_unknown_operator():
    pred = OP("??", 5)
    assert pred(5, None) is False


def test_type_matches_class_name():
    pred = TYPE("Foo")
    assert pred(Foo(), None) is True


def test_type_returns_false_for_other_type():
    pred = TYPE("Foo")
    assert pred(Bar(), None) is False


def test_type_returns_false_for_none():
    pred = TYPE("Foo")
    assert pred(None, None) is False


def test_not_inverts_true_result():
    pred = NOT(ANY())
    assert pred("anything", None) is False


def test_not_inverts_false_result():
    pred = NOT(REGEX(r"^test_"))
    assert pred("abc", None) is True


def test_not_returns_false_when_inner_predicate_raises():
    class BrokenPredicate:
        def __call__(self, actual, node):
            raise RuntimeError("boom")

    pred = NOT(BrokenPredicate())
    assert pred("x", None) is False


class ArgsObj:
    def __init__(
        self,
        posonlyargs=None,
        args=None,
        kwonlyargs=None,
        vararg=None,
        kwarg=None,
    ):
        self.posonlyargs = posonlyargs
        self.args = args
        self.kwonlyargs = kwonlyargs
        self.vararg = vararg
        self.kwarg = kwarg


class FuncNode:
    def __init__(self, args=None):
        self.args = args


def test_arg_count_gt_returns_false_when_node_has_no_args():
    pred = arg_count_gt(0)
    node = DummyNode()
    assert pred(node) is False


def test_arg_count_gt_counts_regular_args():
    pred = arg_count_gt(2)
    node = FuncNode(args=ArgsObj(args=[1, 2, 3]))
    assert pred(node) is True


def test_arg_count_gt_respects_limit_exactly():
    pred = arg_count_gt(3)
    node = FuncNode(args=ArgsObj(args=[1, 2, 3]))
    assert pred(node) is False


def test_arg_count_gt_counts_posonly_args():
    pred = arg_count_gt(1, include_posonly=True, include_args=False)
    node = FuncNode(args=ArgsObj(posonlyargs=[1, 2], args=[3, 4]))
    assert pred(node) is True


def test_arg_count_gt_counts_kwonly_args_when_enabled():
    pred = arg_count_gt(0, include_args=False, include_kwonly=True)
    node = FuncNode(args=ArgsObj(args=[1], kwonlyargs=[2]))
    assert pred(node) is True


def test_arg_count_gt_counts_vararg_when_enabled():
    pred = arg_count_gt(0, include_args=False, include_vararg=True)
    node = FuncNode(args=ArgsObj(vararg="args"))
    assert pred(node) is True


def test_arg_count_gt_counts_kwarg_when_enabled():
    pred = arg_count_gt(0, include_args=False, include_kwarg=True)
    node = FuncNode(args=ArgsObj(kwarg="kwargs"))
    assert pred(node) is True


def test_arg_count_gt_combines_selected_argument_kinds():
    pred = arg_count_gt(
        3,
        include_posonly=True,
        include_args=True,
        include_kwonly=True,
        include_vararg=True,
        include_kwarg=True,
    )
    node = FuncNode(
        args=ArgsObj(
            posonlyargs=[1],
            args=[2],
            kwonlyargs=[3],
            vararg="args",
            kwarg="kwargs",
        )
    )
    assert pred(node) is True


class Module:
    parent = None


class If:
    def __init__(self, parent=None):
        self.parent = parent


class For:
    def __init__(self, parent=None):
        self.parent = parent


class Expr:
    def __init__(self, parent=None):
        self.parent = parent


def test_parent_depth_at_least_returns_false_without_parents():
    node = Expr(parent=None)
    pred = parent_depth_at_least("If", 1)
    assert pred(node) is False


def test_parent_depth_at_least_matches_single_parent():
    node = Expr(parent=If())
    pred = parent_depth_at_least("If", 1)
    assert pred(node) is True


def test_parent_depth_at_least_counts_multiple_matching_parents():
    node = Expr(parent=If(parent=If(parent=Module())))
    pred = parent_depth_at_least("If", 2)
    assert pred(node) is True


def test_parent_depth_at_least_returns_false_when_depth_is_too_small():
    node = Expr(parent=If(parent=Module()))
    pred = parent_depth_at_least("If", 2)
    assert pred(node) is False


def test_parent_depth_at_least_supports_union_string():
    node = Expr(parent=If(parent=For(parent=Module())))
    pred = parent_depth_at_least("If|For", 2)
    assert pred(node) is True


def test_parent_depth_at_least_supports_iterable_of_types():
    node = Expr(parent=If(parent=For(parent=Module())))
    pred = parent_depth_at_least({"If", "For"}, 2)
    assert pred(node) is True


def test_parent_depth_at_least_ignores_non_matching_parents():
    node = Expr(parent=Expr(parent=If(parent=Module())))
    pred = parent_depth_at_least("If", 1)
    assert pred(node) is True


class ValueNode:
    def __init__(self, value):
        self.value = value


def test_val_eq_matches_raw_value():
    pred = VAL_EQ(42)
    assert pred(42, None) is True


def test_val_eq_matches_node_value():
    pred = VAL_EQ(42)
    assert pred(ValueNode(42), None) is True


def test_val_eq_returns_false_for_different_value():
    pred = VAL_EQ(42)
    assert pred(ValueNode(7), None) is False


def test_val_eq_matches_string_value():
    pred = VAL_EQ("hello")
    assert pred(ValueNode("hello"), None) is True