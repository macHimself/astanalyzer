# -------------------------
# CX-001 TooManyArguments
# -------------------------

def test_too_many_arguments_does_not_count_self(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "class A:\n"
        "    def f(self, a, b, c, d, e):\n"
        "        return a\n",
    )

    # pokud se self nepočítá, nemá to matchnout
    assert "CX-001" not in rule_ids


def test_too_many_arguments_does_not_count_cls(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "class A:\n"
        "    @classmethod\n"
        "    def f(cls, a, b, c, d, e):\n"
        "        return a\n",
    )

    assert "CX-001" not in rule_ids


def test_too_many_arguments_constructor_not_flagged(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "class User:\n"
        "    def __init__(self, a, b, c, d, e):\n"
        "        self.a = a\n"
        "        self.b = b\n"
        "        self.c = c\n"
        "        self.d = d\n"
        "        self.e = e\n",
    )

    # designově můžeš chtít NEhlásit __init__
    assert "CX-001" not in rule_ids


# -------------------------
# CX-002 TooDeepNesting
# -------------------------

def test_too_deep_nesting_does_not_match_elif_chain(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(x):\n"
        "    if x == 1:\n"
        "        return 1\n"
        "    elif x == 2:\n"
        "        return 2\n"
        "    elif x == 3:\n"
        "        return 3\n"
        "    else:\n"
        "        return 0\n",
    )

    # elif by neměl být brán jako další úroveň vnoření
    assert "CX-002" not in rule_ids


def test_too_deep_nesting_does_not_cross_function_boundary(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def outer():\n"
        "    if a:\n"
        "        for x in xs:\n"
        "            while x:\n"
        "                pass\n"
        "\n"
        "def inner():\n"
        "    if b:\n"
        "        return b\n",
    )

    # inner funkce nemá inheritnout depth z outer
    assert "CX-002" not in rule_ids


def test_too_deep_nesting_does_not_flag_try_if_combo(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    try:\n"
        "        x = 1\n"
        "    except Exception:\n"
        "        return None\n"
        "\n"
        "    if x:\n"
        "        return x\n",
    )

    # běžná struktura, neměla by být flagged
    assert "CX-002" not in rule_ids


# -------------------------
# CX-003 FunctionTooLong
# -------------------------

def test_function_too_long_does_not_match_docstring_only(scan_rule_ids):
    source = (
        "def f():\n"
        + "".join(f"    '''line {i}'''\n" for i in range(41))
        + "    return 1\n"
    )

    rule_ids = scan_rule_ids(source)

    # dlouhý docstring ≠ komplexní funkce
    assert "CX-003" not in rule_ids


def test_function_too_long_does_not_match_comment_heavy_function(scan_rule_ids):
    source = (
        "def f():\n"
        + "".join(f"    # comment {i}\n" for i in range(45))
        + "    return 1\n"
    )

    rule_ids = scan_rule_ids(source)

    assert "CX-003" not in rule_ids


def test_function_too_long_does_not_match_large_string_literal(scan_rule_ids):
    source = (
        "def f():\n"
        "    query = '''\n"
        + "".join(f"    line {i}\n" for i in range(45))
        + "    '''\n"
        "    return query\n"
    )

    rule_ids = scan_rule_ids(source)

    # velký string není dlouhá logika
    assert "CX-003" not in rule_ids


def test_function_too_long_does_not_match_large_docstring(scan_rule_ids):
    source = (
        "def f():\n"
        "    '''\n"
        + "".join(f"    line {i}\n" for i in range(41))
        + "    '''\n"
        "    return 1\n"
    )
    rule_ids = scan_rule_ids(source)
    assert "CX-003" not in rule_ids
