from astanalyzer.matcher import match
from astanalyzer.matcher import MatchResult


def test_matcher_matches_node_type(parse_code):
    tree = parse_code("def f():\n    return 1\n")
    fn = next(tree.get_children())

    m = match("FunctionDef")

    assert m.evaluate(fn)


def test_matcher_rejects_wrong_node_type(parse_code):
    tree = parse_code("x = 1\n")
    assign = next(tree.get_children())

    m = match("FunctionDef")

    assert not m.evaluate(assign)


def test_matcher_supports_union_node_types(parse_code):
    tree = parse_code("if x:\n    pass\n")
    if_node = next(tree.get_children())

    m = match("If|For|While")

    assert m.evaluate(if_node)


def test_find_matches_returns_all_matching_nodes(parse_code):
    tree = parse_code(
        "def a():\n    pass\n\n"
        "def b():\n    pass\n"
    )

    m = match("FunctionDef")
    found = m.find_matches(tree)

    assert len(found) == 2
    assert {node.name for node in found} == {"a", "b"}


def test_match_result_returns_matchresult_on_success(parse_code):
    tree = parse_code("def f():\n    pass\n")
    fn = next(tree.get_children())

    result = match("FunctionDef").match_result(fn, {})

    assert isinstance(result, MatchResult)
    assert result.node is fn


def test_match_result_returns_none_on_failure(parse_code):
    tree = parse_code("x = 1\n")
    assign = next(tree.get_children())

    result = match("FunctionDef").match_result(assign, {})

    assert result is None


def test_and_combines_matchers(parse_code):
    tree = parse_code("def hello():\n    pass\n")
    fn = next(tree.get_children())

    m = match("FunctionDef").and_(match("FunctionDef").where("name", "hello"))

    assert m.evaluate(fn)


def test_or_combines_matchers(parse_code):
    tree = parse_code("def hello():\n    pass\n")
    fn = next(tree.get_children())

    m = match("ClassDef").or_(match("FunctionDef"))

    assert m.evaluate(fn)

def test_or_left_branch_matches(parse_code):
    tree = parse_code("def f(): pass\n")
    fn = next(tree.get_children())

    m = match("FunctionDef").or_(match("ClassDef"))

    assert m.evaluate(fn)


def test_or_both_fail(parse_code):
    tree = parse_code("x = 1\n")
    assign = next(tree.get_children())

    m = match("FunctionDef").or_(match("ClassDef"))

    assert not m.evaluate(assign)


def test_not_negates_match_result(parse_code):
    tree = parse_code("x = 1\n")
    assign = next(tree.get_children())

    m = match("FunctionDef").not_()

    assert m.evaluate(assign)


def test_has_child_type(parse_code):
    tree = parse_code("def f():\n    return 1\n")
    fn = next(tree.get_children())

    m = match("FunctionDef").has("Return")

    assert m.evaluate(fn)


def test_missing_child_type(parse_code):
    tree = parse_code("def f():\n    pass\n")
    fn = next(tree.get_children())

    m = match("FunctionDef").missing("Return")

    assert m.evaluate(fn)


def test_with_child_nested_matcher(parse_code):
    tree = parse_code("def f():\n    return 1\n")
    fn = next(tree.get_children())

    m = match("FunctionDef").with_child(match("Return"))

    assert m.evaluate(fn)


def test_with_descendant_matches_nested_node(parse_code):
    tree = parse_code(
        "def f():\n"
        "    if x:\n"
        "        print(x)\n"
    )
    fn = next(tree.get_children())

    m = match("FunctionDef").with_descendant(
        match("Call").where_call(name="print")
    )

    assert m.evaluate(fn)


def test_without_descendant_rejects_nested_node(parse_code):
    tree = parse_code(
        "def f():\n"
        "    print(x)\n"
    )
    fn = next(tree.get_children())

    m = match("FunctionDef").without_descendant(
        match("Call").where_call(name="print")
    )

    assert not m.evaluate(fn)


def test_in_attr_matches_only_inside_specific_attribute(parse_code):
    tree = parse_code("if print(x):\n    pass\n")
    if_node = next(tree.get_children())

    m = match("If").in_attr(
        "test",
        match("Call").where_call(name="print"),
    )

    assert m.evaluate(if_node)


def test_in_body_matches_nested_body_content(parse_code):
    tree = parse_code(
        "if x:\n"
        "    print(x)\n"
    )
    if_node = next(tree.get_children())

    m = match("If").in_body(
        match("Call").where_call(name="print")
    )

    assert m.evaluate(if_node)


def test_next_sibling_matches(parse_code):
    tree = parse_code(
        "x = 1\n"
        "y = 2\n"
    )
    first = list(tree.get_children())[0]

    m = match("Assign").next_sibling(match("Assign"))

    assert m.evaluate(first)


def test_previous_sibling_matches(parse_code):
    tree = parse_code(
        "x = 1\n"
        "y = 2\n"
    )
    second = list(tree.get_children())[1]

    m = match("Assign").previous_sibling(match("Assign"))

    assert m.evaluate(second)


def test_later_in_block_matches(parse_code):
    tree = parse_code(
        "x = 1\n"
        "print(x)\n"
    )
    first = list(tree.get_children())[0]

    m = match("Assign").later_in_block(
        match("Expr").with_child(
            match("Call").where_call(name="print")
        )
    )

    assert m.evaluate(first)


def test_capture_stores_reference(parse_code):
    tree = parse_code("x = 1\n")
    assign = next(tree.get_children())

    result = match("Assign").capture("target", "targets.0").match_result(assign, {})

    assert result is not None
    assert "target" in result.refs