# -------------------------
# DEAD-001 / DEAD-003
# -------------------------

def test_unused_variable_does_not_match_when_used_in_return(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    x = 1\n"
        "    return x\n",
    )

    assert "DEAD-001" not in rule_ids
    assert "DEAD-003" not in rule_ids


def test_unused_variable_does_not_match_when_used_in_call(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    x = 1\n"
        "    print(x)\n",
    )

    assert "DEAD-001" not in rule_ids
    assert "DEAD-003" not in rule_ids


def test_unused_variable_does_not_match_when_used_in_if_condition(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    x = 1\n"
        "    if x:\n"
        "        return True\n"
        "    return False\n",
    )

    assert "DEAD-001" not in rule_ids
    assert "DEAD-003" not in rule_ids


def test_unused_variable_does_not_match_when_used_in_f_string(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    name = 'Adam'\n"
        "    return f'Hello {name}'\n",
    )

    assert "DEAD-001" not in rule_ids
    assert "DEAD-003" not in rule_ids


def test_unused_variable_does_not_match_when_used_in_nested_function(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def outer():\n"
        "    x = 1\n"
        "    def inner():\n"
        "        return x\n"
        "    return inner()\n",
    )

    assert "DEAD-001" not in rule_ids
    assert "DEAD-003" not in rule_ids


def test_unused_variable_does_not_match_when_used_in_lambda(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    x = 1\n"
        "    g = lambda: x\n"
        "    return g()\n",
    )

    assert "DEAD-001" not in rule_ids
    assert "DEAD-003" not in rule_ids


def test_unused_variable_does_not_match_when_used_in_comprehension(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    limit = 3\n"
        "    return [i for i in range(limit)]\n",
    )

    assert "DEAD-001" not in rule_ids
    assert "DEAD-003" not in rule_ids


def test_unused_assignment_keep_value_does_not_match_tuple_unpacking(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    a, b = pair()\n"
        "    return 1\n",
    )

    # DEAD-003 je jen pro simple single-name assignment
    assert "DEAD-003" not in rule_ids


def test_unused_assignment_keep_value_does_not_match_attribute_assignment(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(obj):\n"
        "    obj.value = make_value()\n"
        "    return 1\n",
    )

    assert "DEAD-003" not in rule_ids


def test_unused_assignment_keep_value_does_not_match_subscript_assignment(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(items):\n"
        "    items[0] = compute()\n"
        "    return 1\n",
    )

    assert "DEAD-003" not in rule_ids


def test_unused_assignment_keep_value_does_not_match_chained_assignment(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    a = b = compute()\n"
        "    return 1\n",
    )

    assert "DEAD-003" not in rule_ids


# -------------------------
# DEAD-002
# -------------------------

def test_unreachable_code_does_not_match_return_as_last_statement(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    return 1\n",
    )

    assert "DEAD-002" not in rule_ids


def test_unreachable_code_does_not_match_raise_as_last_statement(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    raise ValueError('x')\n",
    )

    assert "DEAD-002" not in rule_ids


def test_unreachable_code_does_not_match_break_as_last_statement(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "for x in xs:\n"
        "    break\n",
    )

    assert "DEAD-002" not in rule_ids


def test_unreachable_code_does_not_match_continue_as_last_statement(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "for x in xs:\n"
        "    continue\n",
    )

    assert "DEAD-002" not in rule_ids


def test_unreachable_code_does_not_cross_function_boundary(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def outer():\n"
        "    def inner():\n"
        "        return 1\n"
        "    x = 2\n"
        "    return x\n",
    )

    # return uvnitř inner() nesmí způsobit DEAD-002 v outer()
    assert "DEAD-002" not in rule_ids


def test_unreachable_code_does_not_match_terminal_statement_without_same_block_sibling(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(flag):\n"
        "    if flag:\n"
        "        return 1\n"
        "    else:\n"
        "        return 2\n",
    )

    assert "DEAD-002" not in rule_ids


def test_unreachable_code_does_not_match_break_without_following_statement_in_same_block(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "for x in xs:\n"
        "    if x:\n"
        "        break\n",
    )

    assert "DEAD-002" not in rule_ids