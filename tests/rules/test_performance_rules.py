def test_print_in_list_comprehension_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "[print(i) for i in xs]\n",
    )

    assert "PERF-001" in rule_ids


def test_useless_list_comprehension_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "[x * 2 for x in xs]\n",
    )

    assert "PERF-002" in rule_ids


def test_useless_list_comprehension_not_detected_when_assigned(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "result = [x * 2 for x in xs]\n",
    )

    assert "PERF-002" not in rule_ids


def test_redundant_sort_before_min_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "x = min(sorted(values))\n",
    )

    assert "PERF-003" in rule_ids


def test_redundant_sort_before_max_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "x = max(sorted(values))\n",
    )

    assert "PERF-003" in rule_ids


def test_redundant_sort_before_min_not_detected_without_sorted(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "x = min(values)\n",
    )

    assert "PERF-003" not in rule_ids


def test_unnecessary_copy_matches_nested_list(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "x = list(list(values))\n",
    )

    assert "PERF-004" in rule_ids


def test_unnecessary_copy_matches_list_literal_wrapper(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "x = list([1, 2, 3])\n",
    )

    assert "PERF-004" in rule_ids


def test_unnecessary_copy_not_detected_for_single_list_conversion(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "x = list(values)\n",
    )

    assert "PERF-004" not in rule_ids


def test_double_loop_same_collection_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "for x in items:\n"
        "    for y in items:\n"
        "        print(x, y)\n",
    )

    assert "PERF-005" in rule_ids


def test_double_loop_same_collection_not_detected_for_different_iterables(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "for x in items:\n"
        "    for y in others:\n"
        "        print(x, y)\n",
    )

    assert "PERF-005" not in rule_ids


def test_loop_could_be_comprehension_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "result = []\n"
        "for x in xs:\n"
        "    result.append(x * 2)\n",
    )

    assert "PERF-006" in rule_ids


def test_loop_could_be_comprehension_not_detected_for_plain_for_loop(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "for x in xs:\n"
        "    print(x)\n",
    )

    assert "PERF-006" not in rule_ids


def test_join_on_generator_matches_listcomp(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "x = ','.join([str(i) for i in xs])\n",
    )

    assert "PERF-007" in rule_ids


def test_join_on_generator_matches_list_wrapped_generator(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "x = ','.join(list(str(i) for i in xs))\n",
    )

    assert "PERF-007" in rule_ids


def test_join_on_generator_not_detected_for_real_generator(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "x = ','.join(str(i) for i in xs)\n",
    )

    assert "PERF-007" not in rule_ids


def test_loop_could_be_comprehension_matches_simple_append(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(xs):\n"
        "    result = []\n"
        "    for x in xs:\n"
        "        result.append(x)\n"
        "    return result\n",
    )

    assert "PERF-006" in rule_ids

def test_loop_could_be_comprehension_matches_filtered_append(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(xs):\n"
        "    result = []\n"
        "    for x in xs:\n"
        "        if is_valid(x):\n"
        "            result.append(normalize(x))\n"
        "    return result\n",
    )

    assert "PERF-006" in rule_ids
