def test_too_many_arguments_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(a, b, c, d, e, f):\n"
        "    return a\n",
    )

    assert "COMPLEX-001" in rule_ids


def test_too_many_arguments_does_not_match_small_function(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(a, b):\n"
        "    return a + b\n",
    )

    assert "COMPLEX-001" not in rule_ids


def test_too_many_arguments_matches_async_function(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "async def f(a, b, c, d, e, f):\n"
        "    return a\n",
    )

    assert "COMPLEX-001" in rule_ids


def test_too_many_arguments_does_not_match_exact_threshold(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(a, b, c, d, e):\n"
        "    return a\n",
    )

    assert "COMPLEX-001" not in rule_ids


def test_too_deep_nesting_matches_nested_ifs(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "if a:\n"
        "    if b:\n"
        "        if c:\n"
        "            if d:\n"
        "                print(d)\n",
    )

    assert "STRUCTURE-001" in rule_ids


def test_too_deep_nesting_not_detected_for_shallow_nesting(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "if a:\n"
        "    if b:\n"
        "        print(b)\n",
    )

    assert "STRUCTURE-001" not in rule_ids


def test_too_deep_nesting_matches_mixed_control_flow(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "if a:\n"
        "    for x in xs:\n"
        "        while x:\n"
        "            if y:\n"
        "                print(x, y)\n",
    )

    assert "STRUCTURE-001" in rule_ids


def test_too_deep_nesting_matches_try_inside_if_chain(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "if a:\n"
        "    if b:\n"
        "        try:\n"
        "            if c:\n"
        "                print(c)\n"
        "        except Exception:\n"
        "            pass\n",
    )

    assert "STRUCTURE-001" in rule_ids  


def test_function_too_long_matches(scan_rule_ids):
    source = (
        "def f():\n"
        + "".join(f"    x{i} = {i}\n" for i in range(41))
    )

    rule_ids = scan_rule_ids(source)

    assert "STRUCTURE-002" in rule_ids


def test_function_too_long_does_not_match_short_function(scan_rule_ids):
    source = (
        "def f():\n"
        "    x = 1\n"
        "    y = 2\n"
        "    return x + y\n"
    )

    rule_ids = scan_rule_ids(source)

    assert "STRUCTURE-002" not in rule_ids


def test_function_too_long_does_not_match_exact_threshold(scan_rule_ids):
    source = (
        "def f():\n"
        + "".join(f"    x{i} = {i}\n" for i in range(39))
    )

    rule_ids = scan_rule_ids(source)

    assert "STRUCTURE-002" not in rule_ids


def test_function_too_long_matches_large_function(scan_rule_ids):
    source = (
        "def f():\n"
        + "".join(f"    x{i} = {i}\n" for i in range(60))
    )

    rule_ids = scan_rule_ids(source)

    assert "STRUCTURE-002" in rule_ids


def test_function_too_long_matches_async_function(scan_rule_ids):
    source = (
        "async def f():\n"
        + "".join(f"    x{i} = {i}\n" for i in range(40))
    )

    rule_ids = scan_rule_ids(source)

    assert "STRUCTURE-002" in rule_ids