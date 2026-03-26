from astanalyzer.rules.performance import RedundantSortBeforeMinMax, JoinOnGenerator


def test_redundant_sort_before_min_matches(parse_code):
    tree = parse_code("x = min(sorted(values))\n")
    assign = next(tree.get_children())
    call = assign.value

    rule = RedundantSortBeforeMinMax()
    matches = rule.match_node(call, ctx={})

    assert len(matches) == 1


def test_join_on_generator_matches_listcomp(parse_code):
    tree = parse_code("x = ','.join([str(i) for i in xs])\n")
    assign = next(tree.get_children())
    call = assign.value

    rule = JoinOnGenerator()
    matches = rule.match_node(call, ctx={})

    assert len(matches) == 1