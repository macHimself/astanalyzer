from astroid import parse
from astanalyzer.matcher import match


def test_matcher_finds_function_without_docstring():
    tree = parse(
        """
def hello():
    return 1
"""
    )

    m = match("FunctionDef").missing_docstring()
    found = m.find_matches(tree)

    assert len(found) == 1
    assert found[0].name == "hello"

def test_compare_none_detection(parse_code):
    tree = parse_code("if x == None:\n    pass\n")

    matcher = match("Compare").where_compare_pairwise(
        op_in=("Eq", "NotEq"),
        any_side_value=None
    )

    matches = matcher.find_matches(tree)

    assert len(matches) == 1