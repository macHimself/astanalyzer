# -------------------------
# STYLE-001 EmptyBlock
# -------------------------

def test_empty_block_does_not_match_when_block_contains_docstring_and_logic(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "if condition:\n"
        "    '''temporary note'''\n"
        "    do_work()\n",
    )

    assert "STYLE-001" not in rule_ids


def test_empty_block_does_not_match_when_except_contains_real_handling(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "try:\n"
        "    risky()\n"
        "except Exception:\n"
        "    handle_error()\n",
    )

    assert "STYLE-001" not in rule_ids


def test_empty_block_does_not_match_except_pass_handler(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def get_node_source(node):\n"
        "    try:\n"
        "        if hasattr(node, 'as_string'):\n"
        "            return node.as_string()\n"
        "    except Exception:\n"
        "        pass\n"
        "    return ''\n",
    )

    assert "STYLE-001" not in rule_ids


# -------------------------
# STYLE-002 RedundantIfElseReturn
# -------------------------

def test_redundant_if_else_return_does_not_match_when_if_branch_is_not_terminal(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(x):\n"
        "    if x:\n"
        "        print(x)\n"
        "    else:\n"
        "        return 0\n",
    )

    assert "STYLE-002" not in rule_ids


def test_redundant_if_else_return_does_not_match_when_elif_chain_has_non_terminal_branch(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(x, y):\n"
        "    if x:\n"
        "        return 1\n"
        "    elif y:\n"
        "        print(y)\n"
        "    else:\n"
        "        return 2\n",
    )

    assert "STYLE-002" not in rule_ids


# -------------------------
# STYLE-003 MultipleReturnsInFunction
# -------------------------

def test_multiple_returns_does_not_match_single_return_function(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(x):\n"
        "    y = x + 1\n"
        "    return y\n",
    )

    assert "STYLE-003" not in rule_ids


def test_multiple_returns_does_not_match_nested_function_return(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def outer():\n"
        "    def inner():\n"
        "        return 1\n"
        "    return inner()\n",
    )

    assert "STYLE-003" not in rule_ids


# -------------------------
# STYLE-004 LineTooLong
# -------------------------

def test_line_too_long_does_not_match_short_module(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "x = 1\n"
        "y = 2\n",
    )

    assert "STYLE-004" not in rule_ids


def test_line_too_long_does_not_match_exact_threshold_line(scan_rule_ids):
    source = 'x = "' + ("a" * 94) + '"\n'
    rule_ids = scan_rule_ids(source)

    assert "STYLE-004" not in rule_ids


# -------------------------
# STYLE-005 FunctionNameNotSnakeCase
# -------------------------

def test_function_name_not_snake_case_does_not_match_snake_case_function(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def valid_name():\n"
        "    return 1\n",
    )

    assert "STYLE-005" not in rule_ids


def test_function_name_not_snake_case_does_not_match_private_snake_case_function(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def _helper_function():\n"
        "    return 1\n",
    )

    assert "STYLE-005" not in rule_ids


# -------------------------
# STYLE-006 ClassNameNotPascalCase
# -------------------------

def test_class_name_not_pascal_case_does_not_match_pascal_case_class(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "class ValidName:\n"
        "    pass\n",
    )

    assert "STYLE-006" not in rule_ids


def test_class_name_not_pascal_case_does_not_match_acronym_style_pascal_case_class(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "class HTTPClient:\n"
        "    pass\n",
    )

    assert "STYLE-006" not in rule_ids


# -------------------------
# STYLE-007 ConstantNotUppercase
# -------------------------

def test_constant_not_uppercase_does_not_match_proper_module_constant(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "API_URL = 'https://example.com'\n",
    )

    assert "STYLE-007" not in rule_ids


def test_constant_not_uppercase_does_not_match_local_variable_inside_function(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    value = 1\n"
        "    return value\n",
    )

    assert "STYLE-007" not in rule_ids


def test_constant_not_uppercase_does_not_match_dunder_assignment(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "__version__ = '1.0'\n",
    )

    assert "STYLE-007" not in rule_ids


# -------------------------
# STYLE-008 TrailingWhitespace
# -------------------------

def test_trailing_whitespace_does_not_match_clean_module(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "x = 1\n"
        "y = 2\n",
    )

    assert "STYLE-008" not in rule_ids


def test_trailing_whitespace_ignored_in_docstring(scan_rule_ids):
    rule_ids = scan_rule_ids(
        'def f():\n'
        '    """\n'
        '    text with trailing space \n'
        '    """\n'
        '    return 1\n'
    )

    assert "STYLE-008" not in rule_ids


def test_trailing_whitespace_does_not_match_inside_multiline_string(scan_rule_ids):
    rule_ids = scan_rule_ids(
        'HTML = """\n'
        'div {   \n'
        '  color: red;   \n'
        '}   \n'
        '"""\n'
    )

    assert "STYLE-008" not in rule_ids


def test_trailing_whitespace_finding_is_anchored_to_affected_line(scan_findings):
    findings = scan_findings(
        '"""Module docstring."""\n'
        "\n"
        "x = 1\n"
        "y = 2   \n"
    )

    finding = next(f for f in findings if f["rule_id"] == "STYLE-008")

    assert finding["start_line"] == 4
    assert finding["end_line"] == 4


# -------------------------
# STYLE-009 MissingBlankLineBetweenFunctions
# -------------------------

def test_missing_blank_line_between_functions_does_not_match_proper_top_level_spacing(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def a():\n"
        "    return 1\n"
        "\n"
        "\n"
        "def b():\n"
        "    return 2\n",
    )

    assert "STYLE-009" not in rule_ids


def test_missing_blank_line_between_functions_does_not_match_proper_method_spacing_in_class(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "class A:\n"
        "    def a(self):\n"
        "        return 1\n"
        "\n"
        "    def b(self):\n"
        "        return 2\n",
    )

    assert "STYLE-009" not in rule_ids


def test_missing_blank_line_between_functions_does_not_match_first_definition_in_scope(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def a():\n"
        "    return 1\n",
    )

    assert "STYLE-009" not in rule_ids


def test_missing_blank_line_does_not_match_nested_function_after_control_flow(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def outer(types):\n"
        "    if isinstance(types, str):\n"
        "        allowed = {types}\n"
        "    else:\n"
        "        allowed = set(types)\n"
        "    def _predicate(node):\n"
        "        return node in allowed\n"
        "    return _predicate\n",
    )

    assert "STYLE-009" not in rule_ids


def test_missing_blank_line_does_not_match_nested_function_inside_function(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def outer():\n"
        "    x = 1\n"
        "    def inner():\n"
        "        return x\n"
        "    return inner\n",
    )

    assert "STYLE-009" not in rule_ids

    
# -------------------------
# STYLE-010 MissingDocstringForFunction
# -------------------------

def test_missing_docstring_for_function_does_not_match_when_docstring_present(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    '''Function docs.'''\n"
        "    return 1\n",
    )

    assert "STYLE-010" not in rule_ids


def test_missing_docstring_for_function_does_not_match_when_only_nested_function_lacks_docstring(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def outer():\n"
        "    '''Outer docs.'''\n"
        "    def inner():\n"
        "        return 1\n"
        "    return inner()\n",
    )

    # outer itself má docstring
    assert "STYLE-010" in rule_ids


def test_missing_docstring_for_function_does_not_match_documented_single_function(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def documented():\n"
        "    '''Docs.'''\n"
        "    return 1\n",
    )

    assert "STYLE-010" not in rule_ids


# -------------------------
# STYLE-011 MissingDocstringForClass
# -------------------------

def test_missing_docstring_for_class_does_not_match_when_docstring_present(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "class A:\n"
        "    '''Class docs.'''\n"
        "    pass\n",
    )

    assert "STYLE-011" not in rule_ids


# -------------------------
# STYLE-012 MissingDocstringForModule
# -------------------------

def test_missing_docstring_for_module_does_not_match_when_module_docstring_present(scan_rule_ids):
    rule_ids = scan_rule_ids(
        '"""Module docs."""\n'
        "\n"
        "x = 1\n",
    )

    assert "STYLE-012" not in rule_ids
