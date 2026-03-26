from astanalyzer.rules.dead_code import UnusedVariable, UnreachableCode


def test_unused_variable_matches(parse_code):
    tree = parse_code("x = 1\n")
    node = next(tree.get_children())

    rule = UnusedVariable()
    matches = rule.match_node(node, ctx={})

    assert len(matches) == 1


def test_unreachable_code_matches_return_with_sibling(parse_code):
    tree = parse_code(
        "def f():\n"
        "    return 1\n"
        "    x = 2\n"
    )
    fn = next(tree.get_children())
    ret = fn.body[0]

    rule = UnreachableCode()
    matches = rule.match_node(ret, ctx={})

    assert len(matches) == 1