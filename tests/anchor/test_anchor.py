from astroid import parse

from astanalyzer.core.anchor import (
    FindingAnchor,
    build_anchor,
    get_context_hash,
    get_symbol_path,
    get_source_hash,
    normalize_source,
)


def parse_code(code: str):
    tree = parse(code)
    tree.file = "test.py"
    tree.file_content = code
    tree.file_by_lines = code.splitlines(keepends=True)
    return tree


def test_normalize_source_trims_outer_blank_lines_and_trailing_spaces():
    text = "\n\n  x = 1   \n  y = 2\t\n\n"
    normalized = normalize_source(text)

    assert normalized == "  x = 1\n  y = 2"


def test_get_symbol_path_for_nested_function_in_class():
    tree = parse_code(
        "class A:\n"
        "    def outer(self):\n"
        "        def inner():\n"
        "            return 1\n"
        "        return inner()\n"
    )

    cls = next(tree.get_children())
    outer = cls.body[0]
    inner = outer.body[0]

    assert get_symbol_path(cls) == "A"
    assert get_symbol_path(outer) == "A.outer"
    assert get_symbol_path(inner) == "A.outer.inner"


def test_get_source_hash_is_stable_for_same_node_source():
    tree1 = parse_code(
        "def foo():\n"
        "    return 1\n"
    )
    tree2 = parse_code(
        "def foo():\n"
        "    return 1\n"
    )

    fn1 = next(tree1.get_children())
    fn2 = next(tree2.get_children())

    assert get_source_hash(fn1) == get_source_hash(fn2)


def test_get_context_hash_differs_for_different_locations():
    tree1 = parse_code(
        "def foo():\n"
        "    return 1\n"
    )
    tree2 = parse_code(
        "\n"
        "def foo():\n"
        "    return 1\n"
    )

    fn1 = next(tree1.get_children())
    fn2 = next(tree2.get_children())

    assert get_context_hash(fn1) != get_context_hash(fn2)


def test_build_anchor_returns_expected_fields_for_function():
    tree = parse_code(
        "def foo(x):\n"
        "    return x\n"
    )
    fn = next(tree.get_children())

    anchor = build_anchor(
        rule_id="STYLE-002",
        file_path="pkg/test.py",
        match=fn,
    )

    assert isinstance(anchor, FindingAnchor)
    assert anchor.rule_id == "STYLE-002"
    assert anchor.file == "pkg/test.py"
    assert anchor.node_type == "FunctionDef"
    assert anchor.symbol_path == "foo"
    assert anchor.line == 1
    assert anchor.col == 0
    assert anchor.end_line == 2
    assert anchor.source_hash
    assert anchor.context_hash
    assert anchor.anchor_id


def test_build_anchor_is_stable_for_same_input():
    code = (
        "def foo(x):\n"
        "    return x\n"
    )

    tree1 = parse_code(code)
    tree2 = parse_code(code)

    fn1 = next(tree1.get_children())
    fn2 = next(tree2.get_children())

    a1 = build_anchor(rule_id="STYLE-002", file_path="pkg/test.py", match=fn1)
    a2 = build_anchor(rule_id="STYLE-002", file_path="pkg/test.py", match=fn2)

    assert a1 == a2
    assert a1.anchor_id == a2.anchor_id


def test_build_anchor_changes_when_rule_id_changes():
    tree = parse_code(
        "def foo():\n"
        "    return 1\n"
    )
    fn = next(tree.get_children())

    a1 = build_anchor(rule_id="STYLE-002", file_path="pkg/test.py", match=fn)
    a2 = build_anchor(rule_id="FUNC-001", file_path="pkg/test.py", match=fn)

    assert a1.anchor_id != a2.anchor_id


def test_build_anchor_changes_when_file_path_changes():
    tree = parse_code(
        "def foo():\n"
        "    return 1\n"
    )
    fn = next(tree.get_children())

    a1 = build_anchor(rule_id="STYLE-002", file_path="pkg/a.py", match=fn)
    a2 = build_anchor(rule_id="STYLE-002", file_path="pkg/b.py", match=fn)

    assert a1.anchor_id != a2.anchor_id


def test_build_anchor_changes_when_source_changes():
    tree1 = parse_code(
        "def foo():\n"
        "    return 1\n"
    )
    tree2 = parse_code(
        "def foo():\n"
        "    return 2\n"
    )

    fn1 = next(tree1.get_children())
    fn2 = next(tree2.get_children())

    a1 = build_anchor(rule_id="STYLE-002", file_path="pkg/test.py", match=fn1)
    a2 = build_anchor(rule_id="STYLE-002", file_path="pkg/test.py", match=fn2)

    assert a1.source_hash != a2.source_hash
    assert a1.anchor_id != a2.anchor_id
