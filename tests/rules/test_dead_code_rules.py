def test_unused_variable_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    x = 1\n"
        "    return 0\n",
    )

    assert "DEAD-001" in rule_ids


def test_unused_variable_not_detected_when_used(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    x = 1\n"
        "    return x\n",
    )

    assert "DEAD-001" not in rule_ids


def test_unreachable_code_after_return_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    return 1\n"
        "    x = 2\n",
    )

    assert "DEAD-002" in rule_ids


def test_unreachable_code_after_raise_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    raise ValueError('x')\n"
        "    y = 2\n",
    )

    assert "DEAD-002" in rule_ids


def test_unreachable_code_after_break_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "for x in xs:\n"
        "    break\n"
        "    print(x)\n",
    )

    assert "DEAD-002" in rule_ids


def test_unreachable_code_after_continue_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "for x in xs:\n"
        "    continue\n"
        "    print(x)\n",
    )

    assert "DEAD-002" in rule_ids


def test_unreachable_code_not_detected_when_no_following_statement(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    return 1\n",
    )

    assert "DEAD-002" not in rule_ids


def test_unused_assignment_keep_value_detected_for_simple_unused_assign(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    x = print('hi')\n"
        "    return 1\n",
    )

    assert "DEAD-003" in rule_ids


def test_unused_assignment_keep_value_not_detected_when_variable_is_used(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    x = 1\n"
        "    return x\n",
    )

    assert "DEAD-003" not in rule_ids


def test_unused_assignment_keep_value_not_detected_for_tuple_unpacking(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    a, b = g()\n"
        "    return 1\n",
    )

    assert "DEAD-003" not in rule_ids


def test_unused_assignment_keep_value_not_detected_for_list_unpacking(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    [a, b] = g()\n"
        "    return 1\n",
    )

    assert "DEAD-003" not in rule_ids


def test_unused_assignment_keep_value_not_detected_for_chained_assignment(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    a = b = g()\n"
        "    return 1\n",
    )

    assert "DEAD-003" not in rule_ids


def test_unused_assignment_keep_value_not_detected_for_attribute_assignment(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "class A:\n"
        "    def f(self):\n"
        "        self.x = g()\n"
        "        return 1\n",
    )

    assert "DEAD-003" not in rule_ids


def test_unused_assignment_keep_value_not_detected_for_subscript_assignment(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(arr):\n"
        "    arr[0] = g()\n"
        "    return 1\n",
    )

    assert "DEAD-003" not in rule_ids


def test_unused_assignment_keep_value_exposes_two_fixers(scan_findings):
    findings = scan_findings(
        "def f():\n"
        "    x = print('hi')\n"
        "    return 1\n",
    )

    finding = next(f for f in findings if f["rule_id"] == "DEAD-003")

    assert len(finding["fixes"]) == 2
    assert finding["fixes"][0]["fixer_index"] == 0
    assert finding["fixes"][1]["fixer_index"] == 1


def test_unused_assignment_keep_value_replace_with_value_preserves_rhs_only(run_scan):
    _, scan = run_scan(
        "def f():\n"
        "    x = print('hi')\n"
        "    return 1\n",
        build_plans=True,
        build_fixes=False,
    )

    finding = next(f for f in scan["findings"] if f["rule_id"] == "DEAD-003")
    fix = finding["fixes"][1]
    
    assert fix["fixer_index"] == 1
    assert fix["dsl"]["because"] == "Keep side effects of the assigned expression, but remove the assignment."
