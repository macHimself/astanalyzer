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


def test_unused_variable_does_not_match_when_value_is_used_in_reassignment_rhs(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(text):\n"
        "    _, rest = text.split(':', 1)\n"
        "    rest = rest.strip()\n"
        "    return rest\n",
    )

    assert "DEAD-001" not in rule_ids


def test_unused_variable_does_not_match_when_variable_is_used_on_rhs_before_reassignment(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    x = ' abc '\n"
        "    x = x.strip()\n"
        "    return x\n",
    )

    assert "DEAD-001" not in rule_ids


def test_unused_variable_does_not_match_when_value_is_used_in_condition_before_branch_reassignment(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(rest):\n"
        "    rest = rest.strip()\n"
        "    if rest.startswith('disable'):\n"
        "        rest = rest[len('disable'):].strip()\n"
        "    elif rest.startswith('enable'):\n"
        "        rest = rest[len('enable'):].strip()\n"
        "    else:\n"
        "        return None\n"
        "    return rest\n",
    )

    assert "DEAD-001" not in rule_ids


def test_unused_variable_does_not_match_when_value_is_used_in_condition_before_reassignment(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(rest):\n"
        "    rest = rest.strip()\n"
        "    if rest:\n"
        "        return rest\n"
        "    return None\n",
    )

    assert "DEAD-001" not in rule_ids


def test_unused_variable_does_not_match_when_branch_assignment_is_used_after_if(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(flag):\n"
        "    if flag:\n"
        "        x = 'a'\n"
        "    else:\n"
        "        x = 'b'\n"
        "    return x\n",
    )

    assert "DEAD-001" not in rule_ids
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


def test_unused_variable_does_not_match_module_constant(scan_rule_ids):
    rule_ids = scan_rule_ids(
        'ASSIGN = "Assign"\n',
    )

    assert "DEAD-001" not in rule_ids


def test_unused_variable_does_not_match_class_attribute_constant(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "class NodeType:\n"
        '    ASSIGN = "Assign"\n',
    )

    assert "DEAD-001" not in rule_ids


def test_unused_assignment_keep_value_does_not_match_class_attribute_constant(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "class NodeType:\n"
        '    ASSIGN = "Assign"\n',
    )

    assert "DEAD-003" not in rule_ids


def test_unused_variable_does_not_match_when_flag_is_set_in_nested_branch_and_used_after_loop(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(items, rule_id):\n"
        "    disabled_all = False\n"
        "    disabled_rules = set()\n"
        "    for cmd, ids in items:\n"
        "        if cmd == 'disable':\n"
        "            if '*' in ids:\n"
        "                disabled_all = True\n"
        "            else:\n"
        "                disabled_rules.update(ids)\n"
        "    return disabled_all or rule_id in disabled_rules\n",
    )

    assert "DEAD-001" not in rule_ids


def test_unused_variable_does_not_match_when_value_updates_while_loop_condition(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(node, allowed, min_depth):\n"
        "    depth = 0\n"
        "    p = getattr(node, 'parent', None)\n"
        "    while p is not None:\n"
        "        if p.__class__.__name__ in allowed:\n"
        "            depth += 1\n"
        "        p = getattr(p, 'parent', None)\n"
        "    return depth >= min_depth\n",
    )

    assert "DEAD-001" not in rule_ids


def test_unused_variable_does_not_match_when_value_is_used_in_next_while_iteration_body(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(node):\n"
        "    cur = node\n"
        "    while True:\n"
        "        if cur is None:\n"
        "            return False\n"
        "        tail = cur.children\n"
        "        if not tail:\n"
        "            return True\n"
        "        cur = tail[0]\n",
    )

    assert "DEAD-001" not in rule_ids
    

# test_
def debug_dead_findings(scan_findings):
    findings = scan_findings(
        "def f(rest):\n"
        "    rest = rest.strip()\n"
        "    if rest.startswith('disable'):\n"
        "        rest = rest[len('disable'):].strip()\n"
        "    elif rest.startswith('enable'):\n"
        "        rest = rest[len('enable'):].strip()\n"
        "    else:\n"
        "        return None\n"
        "    return rest\n",
    )

    dead = [
        (f["rule_id"], f["start_line"], f["end_line"], f.get("title"))
        for f in findings
        if f["rule_id"].startswith("DEAD-")
    ]

    print(dead)
    assert False


def test_unused_variable_does_not_match_loop_carried_state(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def pairs(items):\n"
        "    prev = None\n"
        "    for right in items:\n"
        "        yield (prev, right)\n"
        "        prev = right\n",
    )

    assert "DEAD-001" not in rule_ids