# -------------------------
# PERF-001 PrintInListComprehension
# -------------------------

def test_print_in_list_comprehension_does_not_match_when_print_is_shadowed(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(print):\n"
        "    [print(x) for x in range(5)]\n",
    )

    assert "PERF-001" not in rule_ids


def test_print_in_list_comprehension_does_not_match_when_listcomp_is_assigned(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    result = [print(x) for x in range(5)]\n"
        "    return result\n",
    )

    assert "PERF-001" not in rule_ids


# -------------------------
# PERF-002 UselessListComprehension
# -------------------------

def test_useless_list_comprehension_does_not_match_when_assigned(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    xs = [x for x in range(5)]\n"
        "    return xs\n",
    )

    assert "PERF-002" not in rule_ids


def test_useless_list_comprehension_does_not_match_when_returned(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    return [x for x in range(5)]\n",
    )

    assert "PERF-002" not in rule_ids


def test_useless_list_comprehension_does_not_match_when_passed_to_call(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    consume([x for x in range(5)])\n",
    )

    assert "PERF-002" not in rule_ids


# -------------------------
# PERF-003 RedundantSortBeforeMinMax
# -------------------------

def test_redundant_sort_before_minmax_does_not_match_when_min_is_shadowed(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(items):\n"
        "    def min(x):\n"
        "        return x\n"
        "    return min(sorted(items))\n",
    )

    assert "PERF-003" not in rule_ids


def test_redundant_sort_before_minmax_does_not_match_when_max_is_shadowed(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(items):\n"
        "    def max(x):\n"
        "        return x\n"
        "    return max(sorted(items))\n",
    )

    assert "PERF-003" not in rule_ids


def test_redundant_sort_before_minmax_does_not_match_when_sorted_is_shadowed(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(items):\n"
        "    def sorted(x):\n"
        "        return x\n"
        "    return min(sorted(items))\n",
    )

    assert "PERF-003" not in rule_ids


# -------------------------
# PERF-004 UnnecessaryCopy
# -------------------------

def test_unnecessary_copy_does_not_match_defensive_dict_copy_before_mutation(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(d):\n"
        "    local = d.copy()\n"
        "    local['x'] = 1\n"
        "    return local\n",
    )

    assert "PERF-004" not in rule_ids


def test_unnecessary_copy_does_not_match_list_materialization_used_multiple_times(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(items):\n"
        "    snapshot = list(items)\n"
        "    a = len(snapshot)\n"
        "    b = list(reversed(snapshot))\n"
        "    return a, b\n",
    )

    assert "PERF-004" not in rule_ids


def test_unnecessary_copy_does_not_match_set_used_for_normalization(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(items):\n"
        "    unique = set(items)\n"
        "    return sorted(unique)\n",
    )

    assert "PERF-004" not in rule_ids


# -------------------------
# PERF-005 DoubleLoopSameCollection
# -------------------------

def test_double_loop_same_collection_does_not_match_when_inner_iter_is_shadowed(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(items):\n"
        "    for x in items:\n"
        "        items = get_other_items()\n"
        "        for y in items:\n"
        "            print(x, y)\n",
    )

    assert "PERF-005" not in rule_ids


def test_double_loop_same_collection_does_not_match_when_iterables_are_from_distinct_calls(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    for x in get_items():\n"
        "        for y in get_items():\n"
        "            print(x, y)\n",
    )

    assert "PERF-005" not in rule_ids


# -------------------------
# PERF-006 LoopCouldBeComprehension
# -------------------------


def test_loop_could_be_comprehension_does_not_match_when_loop_has_intermediate_step(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(xs):\n"
        "    result = []\n"
        "    for x in xs:\n"
        "        value = transform(x)\n"
        "        result.append(value)\n"
        "    return result\n",
    )

    assert "PERF-006" not in rule_ids


def test_loop_could_be_comprehension_does_not_match_when_loop_has_two_statements(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(xs):\n"
        "    result = []\n"
        "    for x in xs:\n"
        "        audit(x)\n"
        "        result.append(x)\n"
        "    return result\n",
    )

    assert "PERF-006" not in rule_ids


def test_loop_could_be_comprehension_does_not_match_when_if_has_else_branch(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(xs):\n"
        "    result = []\n"
        "    for x in xs:\n"
        "        if is_valid(x):\n"
        "            result.append(normalize(x))\n"
        "        else:\n"
        "            log(x)\n"
        "    return result\n",
    )

    assert "PERF-006" not in rule_ids


def test_loop_could_be_comprehension_does_not_match_when_loop_has_extra_side_effect(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(xs):\n"
        "    result = []\n"
        "    for x in xs:\n"
        "        log(x)\n"
        "        result.append(x)\n"
        "    return result\n",
    )

    assert "PERF-006" not in rule_ids


def test_loop_could_be_comprehension_does_not_match_when_if_body_has_multiple_statements(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(xs):\n"
        "    result = []\n"
        "    for x in xs:\n"
        "        if is_valid(x):\n"
        "            audit(x)\n"
        "            result.append(x)\n"
        "    return result\n",
    )

    assert "PERF-006" not in rule_ids


# -------------------------
# PERF-007 JoinOnGenerator
# -------------------------

def test_join_on_generator_does_not_match_when_join_is_shadowed(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(join, xs):\n"
        "    return join([str(x) for x in xs])\n",
    )

    assert "PERF-007" not in rule_ids


def test_join_on_generator_does_not_match_when_custom_join_method_is_used(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "class Joiner:\n"
        "    def join(self, items):\n"
        "        return items\n"
        "\n"
        "def f(xs):\n"
        "    j = Joiner()\n"
        "    return j.join([str(x) for x in xs])\n",
    )

    assert "PERF-007" not in rule_ids


def test_join_on_generator_does_not_match_when_list_wrapper_is_used_with_custom_join(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "class Joiner:\n"
        "    def join(self, items):\n"
        "        return items\n"
        "\n"
        "def f(xs):\n"
        "    j = Joiner()\n"
        "    return j.join(list(str(x) for x in xs))\n",
    )

    assert "PERF-007" not in rule_ids