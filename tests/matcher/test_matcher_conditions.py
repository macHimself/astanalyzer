from astanalyzer.matcher import match, ref


def test_where_matches_simple_attribute(parse_code):
    tree = parse_code("def hello():\n    return 1\n")
    fn = next(tree.get_children())

    m = match("FunctionDef").where("name", "hello")

    assert m.evaluate(fn)


def test_where_missing_doc_matches_function_without_docstring(parse_code):
    tree = parse_code("def hello():\n    return 1\n")
    fn = next(tree.get_children())

    m = match("FunctionDef").where_missing("doc")

    assert m.evaluate(fn)


def test_where_exists_doc_matches_function_with_docstring(parse_code):
    tree = parse_code('def hello():\n    """doc"""\n    return 1\n')
    fn = next(tree.get_children())

    m = match("FunctionDef").where_exists("doc")

    assert m.evaluate(fn)


def test_where_regex_matches_function_name(parse_code):
    tree = parse_code("def hello_world():\n    return 1\n")
    fn = next(tree.get_children())

    m = match("FunctionDef").where_regex("name", r"^[a-z_]+$")

    assert m.evaluate(fn)


def test_where_len_matches_function_arg_count(parse_code):
    tree = parse_code("def f(a, b):\n    return a + b\n")
    fn = next(tree.get_children())

    m = match("FunctionDef").where_len("args.args", 2)

    assert m.evaluate(fn)


def test_where_node_type_matches_assignment_value(parse_code):
    tree = parse_code("x = print('a')\n")
    assign = next(tree.get_children())

    m = match("Assign").where_node_type("value", "Call")

    assert m.evaluate(assign)


def test_where_call_name_matches_print(parse_code):
    tree = parse_code("print('x')\n")
    expr = next(tree.get_children())
    call = expr.value

    m = match("Call").where_call(name="print")

    assert m.evaluate(call)


def test_where_call_qual_matches_os_system(parse_code):
    tree = parse_code("import os\nos.system('ls')\n")
    nodes_list = list(tree.get_children())
    expr = nodes_list[1]
    call = expr.value

    m = match("Call").where_call(qual="os.system")

    assert m.evaluate(call)


def test_has_parent_matches_call_inside_expr(parse_code):
    tree = parse_code("print('x')\n")
    expr = next(tree.get_children())
    call = expr.value

    m = match("Call").has_parent("Expr")

    assert m.evaluate(call)


def test_missing_parent_matches_open_without_with(parse_code):
    tree = parse_code("f = open('x.txt')\n")
    assign = next(tree.get_children())
    call = assign.value

    m = match("Call").where_call(name="open").missing_parent("With|AsyncWith")

    assert m.evaluate(call)


def test_where_compare_pairwise_matches_none_comparison(parse_code):
    tree = parse_code("if x == None:\n    pass\n")
    if_node = next(tree.get_children())
    compare = if_node.test

    m = match("Compare").where_compare_pairwise(
        op_in=("Eq", "NotEq"),
        any_side_value=None,
    )

    assert m.evaluate(compare)


def test_where_contains_matches_namedexpr_in_if_test(parse_code):
    tree = parse_code("if (x := 1):\n    pass\n")
    if_node = next(tree.get_children())

    m = match("If").where_contains("NamedExpr", in_="test")

    assert m.evaluate(if_node)


def test_where_target_contains_any_matches_password_name(parse_code):
    tree = parse_code("password = 'secret'\n")
    assign = next(tree.get_children())

    m = match("Assign").where_target_contains_any("password", "token", "secret")

    assert m.evaluate(assign)


def test_where_value_is_string_literal_matches_string(parse_code):
    tree = parse_code("password = 'secret'\n")
    assign = next(tree.get_children())

    m = match("Assign").where_value_is_string_literal(non_empty=True)

    assert m.evaluate(assign)


def test_where_value_is_string_literal_rejects_non_string(parse_code):
    tree = parse_code("password = 123\n")
    assign = next(tree.get_children())

    m = match("Assign").where_value_is_string_literal(non_empty=True)

    assert not m.evaluate(assign)


def test_where_mutable_default_argument_matches_list_default(parse_code):
    tree = parse_code("def f(x=[]):\n    return x\n")
    fn = next(tree.get_children())

    m = match("FunctionDef").where_mutable_default_argument()

    assert m.evaluate(fn)


def test_where_mutable_default_argument_rejects_none_default(parse_code):
    tree = parse_code("def f(x=None):\n    return x\n")
    fn = next(tree.get_children())

    m = match("FunctionDef").where_mutable_default_argument()

    assert not m.evaluate(fn)


def test_where_same_text_matches_captured_ancestor_iter(parse_code):
    tree = parse_code(
        "for x in items:\n"
        "    for y in items:\n"
        "        print(y)\n"
    )
    outer = next(tree.get_children())
    inner = outer.body[0]

    m = (
        match("For")
        .capture_ancestor("outer", "For")
        .same_iter_as_ancestor("outer")
    )

    assert m.evaluate(inner)
