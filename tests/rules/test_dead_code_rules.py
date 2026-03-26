def test_unused_variable_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    x = 1\n"
        "    return 0\n",
    )

    assert "VAR-001" in rule_ids


def test_unused_variable_not_detected_when_used(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    x = 1\n"
        "    return x\n",
    )

    assert "VAR-001" not in rule_ids


def test_unreachable_code_after_return_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    return 1\n"
        "    x = 2\n",
    )

    assert "FLOW-001" in rule_ids


def test_unreachable_code_after_raise_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    raise ValueError('x')\n"
        "    y = 2\n",
    )

    assert "FLOW-001" in rule_ids


def test_unreachable_code_after_break_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "for x in xs:\n"
        "    break\n"
        "    print(x)\n",
    )

    assert "FLOW-001" in rule_ids


def test_unreachable_code_after_continue_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "for x in xs:\n"
        "    continue\n"
        "    print(x)\n",
    )

    assert "FLOW-001" in rule_ids


def test_unreachable_code_not_detected_when_no_following_statement(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    return 1\n",
    )

    assert "FLOW-001" not in rule_ids