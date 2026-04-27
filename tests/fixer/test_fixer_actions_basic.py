from astanalyzer.fixer import fix


def test_comment_before_builds_comment(parse_code):
    code = "x = 1\n"
    tree = parse_code(code, "sample.py")
    node = next(tree.get_children())

    proposal = (
        fix()
        .comment_before("TODO")
        .because("Test")
        .build(node)
    )

    assert "# TODO" in proposal.suggestion

def test_replace_none_comparison_operator(parse_code):
    code = (
        "if x == None:\n"
        "    pass\n"
    )
    tree = parse_code(code, "sample.py")
    if_node = next(tree.get_children())
    compare = if_node.test

    proposal = (
        fix()
        .replace_none_comparison_operator()
        .because("Use is None")
        .build(compare)
    )

    assert "x is None" in proposal.suggestion

def test_remove_dead_code_after_return(parse_code):
    code = (
        "def f():\n"
        "    return 1\n"
        "    x = 2\n"
    )
    tree = parse_code(code, "sample.py")
    fn = next(tree.get_children())
    ret = fn.body[0]

    proposal = (
        fix()
        .remove_dead_code_after()
        .because("Dead code")
        .build(ret)
    )

    assert "x = 2" not in proposal.suggestion
    assert "return 1" in proposal.suggestion


def test_review_note_and_ignore_inserts_note_and_ignore(parse_code):
    module = parse_code(
        """
def foo(a, b, c, d, e, f):
    return a
"""
    )
    node = module.body[0]

    proposal = (
        fix()
        .add_review_note_and_ignore("CX-001", "Too many parameters.")
        .because("test")
        .build(node)
    )

    assert "# Too many parameters." in proposal.suggestion
    assert "# astanalyzer: ignore-next CX-001" in proposal.suggestion

    lines = proposal.suggestion.splitlines()
    assert lines[0] == "# Too many parameters."
    assert lines[1] == "# astanalyzer: ignore-next CX-001"
    assert lines[2].startswith("def foo")
