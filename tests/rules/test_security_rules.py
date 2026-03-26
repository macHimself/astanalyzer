from astanalyzer.rules.security import UseOfEval, OpenWithoutWith


def test_use_of_eval_matches(parse_code):
    tree = parse_code("eval('1 + 1')\n")
    expr = next(tree.get_children())
    call = expr.value

    rule = UseOfEval()
    matches = rule.match_node(call, ctx={})

    assert len(matches) == 1


def test_open_without_with_matches(parse_code):
    tree = parse_code("f = open('x.txt')\n")
    assign = next(tree.get_children())
    call = assign.value

    rule = OpenWithoutWith()
    matches = rule.match_node(call, ctx={})

    assert len(matches) == 1