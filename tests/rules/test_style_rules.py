def test_missing_docstring_detected(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def foo():\n"
        "    return 1\n",
    )

    assert "STYLE-010" in rule_ids


def test_missing_docstring_not_detected_when_present(scan_rule_ids):
    rule_ids = scan_rule_ids(
        'def foo():\n'
        '    """This is a docstring."""\n'
        '    return 1\n',
    )

    assert "STYLE-011" not in rule_ids


def test_missing_class_docstring_detected(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "class MyClass:\n"
        "    pass\n",
    )

    assert "STYLE-011" in rule_ids


def test_missing_module_docstring_detected(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "x = 1\n",
    )

    assert "STYLE-012" in rule_ids


def test_function_name_not_snake_case_detected(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def BadName():\n"
        "    pass\n",
    )

    assert "STYLE-005" in rule_ids


def test_function_name_snake_case_not_detected(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def good_name():\n"
        "    pass\n",
    )

    assert "STYLE-005" not in rule_ids


def test_class_name_not_pascal_case_detected(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "class bad_name:\n"
        "    pass\n",
    )

    assert "STYLE-006" in rule_ids


def test_class_name_pascal_case_not_detected(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "class GoodName:\n"
        "    pass\n",
    )

    assert "STYLE-006" not in rule_ids


def test_constant_not_uppercase_detected(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "my_constant = 1\n",
    )

    assert "STYLE-007" in rule_ids


def test_constant_uppercase_not_detected(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "MY_CONSTANT = 1\n",
    )

    assert "STYLE-007" not in rule_ids


def test_trailing_whitespace_detected(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "x = 1   \n",
    )

    assert "STYLE-008" in rule_ids


def test_missing_blank_line_between_functions_detected(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def a():\n"
        "    pass\n"
        "def b():\n"
        "    pass\n",
    )

    assert "STYLE-009" in rule_ids


def test_line_too_long_detected(scan_rule_ids):
    long_line = "x = '" + ("a" * 120) + "'\n"
    rule_ids = scan_rule_ids(
        long_line,
    )

    assert "STYLE-004" in rule_ids


def test_multiple_returns_detected(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def foo(x):\n"
        "    if x:\n"
        "        return 1\n"
        "    return 2\n",
    )

    assert "STYLE-003" in rule_ids


def test_redundant_else_after_return_detected(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def foo(x):\n"
        "    if x:\n"
        "        return 1\n"
        "    else:\n"
        "        return 2\n",
    )

    assert "STYLE-002" in rule_ids


def test_empty_block_detected(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "if True:\n"
        "    pass\n",
    )

    assert "STYLE-001" in rule_ids


def test_empty_block_still_matches_if_pass(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "if condition:\n"
        "    pass\n",
    )

    assert "STYLE-001" in rule_ids