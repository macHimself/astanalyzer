def test_compare_to_none_using_eq_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(x):\n"
        "    if x == None:\n"
        "        return True\n",
    )

    assert "CMP-001" in rule_ids


def test_compare_to_none_using_is_does_not_match(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(x):\n"
        "    if x is None:\n"
        "        return True\n",
    )

    assert "CMP-001" not in rule_ids


def test_always_true_condition_if_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    if True:\n"
        "        return 1\n",
    )

    assert "COND-001" in rule_ids


def test_always_true_condition_while_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    while True:\n"
        "        break\n",
    )

    assert "COND-003" in rule_ids


def test_assignment_in_condition_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    if (x := 1):\n"
        "        return x\n",
    )

    assert "ASSIGN-001" in rule_ids


def test_redeclared_variable_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    x = 1\n"
        "    x = 2\n"
        "    return x\n",
    )

    assert "VAR-002" in rule_ids


def test_exception_not_used_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "try:\n"
        "    x = 1\n"
        "except Exception as e:\n"
        "    print('fail')\n",
    )

    assert "EXC-015" in rule_ids


def test_exception_not_used_ignored_for_underscore(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "try:\n"
        "    x = 1\n"
        "except Exception as _:\n"
        "    print('fail')\n",
    )

    assert "EXC-015" not in rule_ids


def test_bare_except_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "try:\n"
        "    x = 1\n"
        "except:\n"
        "    pass\n",
    )

    assert "EXC-001" in rule_ids


def test_mutable_default_argument_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(items=[]):\n"
        "    return items\n",
    )

    assert "ARG-017" in rule_ids


def test_mutable_default_argument_not_detected_for_none(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(items=None):\n"
        "    return items\n",
    )

    assert "ARG-017" not in rule_ids


def test_print_debug_statement_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    print('debug')\n",
    )

    assert "DBG-023" in rule_ids


def test_print_debug_statement_not_detected_without_print(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    return 'debug'\n",
    )

    assert "DBG-023" not in rule_ids