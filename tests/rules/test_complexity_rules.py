from astanalyzer.rules.complexity import TooManyArguments
from astroid import parse


def test_too_many_arguments_matches():
    code = """
def f(a, b, c, d, e, f):
    return a
"""
    tree = parse(code)
    fn = next(tree.get_children())

    rule = TooManyArguments()
    matches = rule.match_node(fn, ctx={})

    assert len(matches) == 1

def test_too_many_arguments_does_not_match_small_function():
    code = """
def f(a, b):
    return a + b
"""
    tree = parse(code)
    fn = next(tree.get_children())

    rule = TooManyArguments()
    matches = rule.match_node(fn, ctx={})

    assert matches == []