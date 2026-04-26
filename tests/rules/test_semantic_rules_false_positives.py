# -------------------------
# SEM-001 AlwaysTrueConditionIf
# -------------------------

def test_always_true_condition_if_does_not_match_nonliteral_truthy_name(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(flag):\n"
        "    if flag:\n"
        "        return 1\n",
    )

    assert "SEM-001" not in rule_ids


def test_always_true_condition_if_does_not_match_len_check(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(xs):\n"
        "    if len(xs):\n"
        "        return xs[0]\n",
    )

    assert "SEM-001" not in rule_ids


# -------------------------
# SEM-002 AlwaysTrueConditionWhile
# -------------------------

def test_always_true_condition_while_does_not_match_nonliteral_truthy_name(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(flag):\n"
        "    while flag:\n"
        "        break\n",
    )

    assert "SEM-002" not in rule_ids


def test_always_true_condition_while_does_not_match_function_call_condition(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    while should_continue():\n"
        "        break\n",
    )

    assert "SEM-002" not in rule_ids


# -------------------------
# SEM-003 CompareToNoneUsingEq
# -------------------------

def test_compare_to_none_using_eq_does_not_match_is_none(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(x):\n"
        "    return x is None\n",
    )

    assert "SEM-003" not in rule_ids


def test_compare_to_none_using_eq_does_not_match_is_not_none(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(x):\n"
        "    return x is not None\n",
    )

    assert "SEM-003" not in rule_ids


def test_compare_to_none_using_eq_does_not_match_non_none_equality(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(x):\n"
        "    return x == 0\n",
    )

    assert "SEM-003" not in rule_ids


# -------------------------
# SEM-004 AssignmentInCondition
# -------------------------

def test_assignment_in_condition_does_not_match_assignment_outside_condition(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(data):\n"
        "    item = next(iter(data), None)\n"
        "    if item:\n"
        "        return item\n",
    )

    assert "SEM-004" not in rule_ids


def test_assignment_in_condition_does_not_match_namedexpr_outside_test(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(xs):\n"
        "    return [(y := x + 1) for x in xs]\n",
    )

    assert "SEM-004" not in rule_ids


# -------------------------
# SEM-005 RedeclaredVariable
# -------------------------

def test_redeclared_variable_does_not_match_when_first_value_is_used_before_reassignment(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    x = 1\n"
        "    print(x)\n"
        "    x = 2\n"
        "    return x\n",
    )

    assert "SEM-005" not in rule_ids


def test_redeclared_variable_does_not_match_when_value_is_used_in_if_before_reassignment(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    x = 1\n"
        "    if x:\n"
        "        pass\n"
        "    x = 2\n"
        "    return x\n",
    )

    assert "SEM-005" not in rule_ids


def test_redeclared_variable_does_not_match_when_reassignment_is_in_different_nested_scope(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    x = 1\n"
        "    def inner():\n"
        "        x = 2\n"
        "        return x\n"
        "    return inner()\n",
    )

    assert "SEM-005" not in rule_ids


def test_redeclared_variable_does_not_match_when_reassignment_uses_previous_value(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def normalize_source(text):\n"
        "    lines = text.replace('\\r\\n', '\\n').replace('\\r', '\\n').split('\\n')\n"
        "    lines = [line.rstrip() for line in lines]\n"
        "    return lines\n",
    )

    assert "SEM-005" not in rule_ids


def test_redeclared_variable_does_not_match_for_self_transform_reassignment(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(x):\n"
        "    x = x.strip()\n"
        "    return x\n",
    )

    assert "SEM-005" not in rule_ids


# -------------------------
# SEM-006 ExceptionNotUsed
# -------------------------

def test_exception_not_used_does_not_match_when_exception_is_logged(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    try:\n"
        "        risky()\n"
        "    except Exception as e:\n"
        "        print(e)\n",
    )

    assert "SEM-006" not in rule_ids


def test_exception_not_used_does_not_match_when_exception_is_reraised_with_context(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    try:\n"
        "        risky()\n"
        "    except Exception as e:\n"
        "        raise RuntimeError(str(e))\n",
    )

    assert "SEM-006" not in rule_ids


def test_exception_not_used_does_not_match_when_alias_is_underscore(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    try:\n"
        "        risky()\n"
        "    except Exception as _:\n"
        "        return None\n",
    )

    assert "SEM-006" not in rule_ids


# -------------------------
# SEM-007 BareExcept
# -------------------------

def test_bare_except_does_not_match_except_exception(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    try:\n"
        "        risky()\n"
        "    except Exception:\n"
        "        return None\n",
    )

    assert "SEM-007" not in rule_ids


def test_bare_except_does_not_match_specific_exception(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    try:\n"
        "        risky()\n"
        "    except ValueError:\n"
        "        return None\n",
    )

    assert "SEM-007" not in rule_ids


# -------------------------
# SEM-008 MutableDefaultArgument
# -------------------------

def test_mutable_default_argument_does_not_match_none_default(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(items=None):\n"
        "    if items is None:\n"
        "        items = []\n"
        "    return items\n",
    )

    assert "SEM-008" not in rule_ids


def test_mutable_default_argument_does_not_match_tuple_default(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(items=()):\n"
        "    return items\n",
    )

    assert "SEM-008" not in rule_ids


def test_mutable_default_argument_does_not_match_string_default(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(name='x'):\n"
        "    return name\n",
    )

    assert "SEM-008" not in rule_ids


# -------------------------
# SEM-009 PrintDebugStatement
# -------------------------

def test_print_debug_statement_does_not_match_when_print_is_shadowed(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(print):\n"
        "    print('hello')\n",
    )

    assert "SEM-009" not in rule_ids


def test_print_debug_statement_does_not_match_when_print_is_local_function(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    def print(x):\n"
        "        return x\n"
        "    print('hello')\n",
    )

    assert "SEM-009" not in rule_ids


def test_print_debug_statement_does_not_match_when_print_is_method_on_other_object(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "class Logger:\n"
        "    def print(self, x):\n"
        "        return x\n"
        "\n"
        "def f():\n"
        "    logger = Logger()\n"
        "    logger.print('hello')\n",
    )

    assert "SEM-009" not in rule_ids
