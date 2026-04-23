# -------------------------
# SEC-001 UseOfEval
# -------------------------

def test_use_of_eval_does_not_match_when_eval_is_shadowed(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(eval):\n"
        "    return eval('1 + 1')\n",
    )

    assert "SEC-001" not in rule_ids


def test_use_of_eval_does_not_match_when_exec_is_shadowed(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(exec):\n"
        "    exec('print(1)')\n",
    )

    assert "SEC-001" not in rule_ids


def test_use_of_eval_does_not_match_when_eval_is_local_function(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    def eval(x):\n"
        "        return x\n"
        "    return eval('1 + 1')\n",
    )

    assert "SEC-001" not in rule_ids


def test_use_of_eval_does_not_match_when_exec_is_local_function(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    def exec(x):\n"
        "        return x\n"
        "    return exec('print(1)')\n",
    )

    assert "SEC-001" not in rule_ids


# -------------------------
# SEC-002 EvalLiteralParsingCandidate
# -------------------------

def test_eval_literal_candidate_does_not_match_when_eval_is_shadowed(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(eval):\n"
        "    return eval('[1, 2, 3]')\n",
    )

    assert "SEC-002" not in rule_ids


def test_eval_literal_candidate_does_not_match_for_empty_string_literal(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    return eval('')\n",
    )

    assert "SEC-002" not in rule_ids


def test_eval_literal_candidate_does_not_match_for_non_literal_like_string(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    return eval('x + y')\n",
    )

    assert "SEC-002" not in rule_ids


def test_eval_literal_candidate_does_not_match_when_more_than_one_argument_is_used(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    return eval('1', {})\n",
    )

    assert "SEC-002" not in rule_ids


def test_eval_literal_candidate_does_not_match_when_keywords_are_used(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    return eval(source='1')\n",
    )

    assert "SEC-002" not in rule_ids


# -------------------------
# SEC-003 UseOfOsSystem
# -------------------------

def test_use_of_os_system_does_not_match_when_os_is_shadowed(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(os):\n"
        "    return os.system('ls')\n",
    )

    assert "SEC-003" not in rule_ids


def test_use_of_os_system_does_not_match_when_os_is_local_object(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "class FakeOS:\n"
        "    def system(self, cmd):\n"
        "        return cmd\n"
        "\n"
        "def f():\n"
        "    os = FakeOS()\n"
        "    return os.system('ls')\n",
    )

    assert "SEC-003" not in rule_ids


def test_use_of_os_system_does_not_match_when_popen_is_custom_method(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "class FakeOS:\n"
        "    def popen(self, cmd):\n"
        "        return cmd\n"
        "\n"
        "def f():\n"
        "    os = FakeOS()\n"
        "    return os.popen('ls')\n",
    )

    assert "SEC-003" not in rule_ids


# -------------------------
# SEC-004 HardcodedPasswordOrKey
# -------------------------

def test_hardcoded_secret_does_not_match_for_empty_string(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "password = ''\n",
    )

    assert "SEC-004" not in rule_ids


def test_hardcoded_secret_does_not_match_for_none_value(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "password = None\n",
    )

    assert "SEC-004" not in rule_ids


def test_hardcoded_secret_does_not_match_for_non_string_value(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "token = 12345\n",
    )

    assert "SEC-004" not in rule_ids


def test_hardcoded_secret_does_not_match_for_unrelated_key_name(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "monkey = 'banana'\n",
    )

    # důležitý guard: "key" uvnitř jiného slova nemá spouštět warning
    assert "SEC-004" not in rule_ids


def test_hardcoded_secret_does_not_match_for_keyboard_variable(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "keyboard = 'qwerty'\n",
    )

    assert "SEC-004" not in rule_ids


def test_hardcoded_secret_does_not_match_for_turkey_variable(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "turkey = 'sandwich'\n",
    )

    assert "SEC-004" not in rule_ids


# -------------------------
# SEC-005 InsecureRandom
# -------------------------

def test_insecure_random_does_not_match_when_random_is_shadowed(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(random):\n"
        "    return random.choice([1, 2, 3])\n",
    )

    assert "SEC-005" not in rule_ids


def test_insecure_random_does_not_match_when_random_is_local_object(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "class FakeRandom:\n"
        "    def randint(self, a, b):\n"
        "        return 4\n"
        "\n"
        "def f():\n"
        "    random = FakeRandom()\n"
        "    return random.randint(1, 10)\n",
    )

    assert "SEC-005" not in rule_ids


def test_insecure_random_does_not_match_when_choice_is_unrelated_method_on_other_object(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "class Picker:\n"
        "    def choice(self, xs):\n"
        "        return xs[0]\n"
        "\n"
        "def f():\n"
        "    picker = Picker()\n"
        "    return picker.choice([1, 2, 3])\n",
    )

    assert "SEC-005" not in rule_ids


# -------------------------
# SEC-006 OpenWithoutWith
# -------------------------

def test_open_without_with_does_not_match_when_open_is_shadowed(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f(open):\n"
        "    return open('file.txt')\n",
    )

    assert "SEC-006" not in rule_ids


def test_open_without_with_does_not_match_when_open_is_local_function(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    def open(path):\n"
        "        return path\n"
        "    return open('file.txt')\n",
    )

    assert "SEC-006" not in rule_ids


def test_open_without_with_does_not_match_inside_with(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "def f():\n"
        "    with open('file.txt') as f:\n"
        "        return f.read()\n",
    )

    assert "SEC-006" not in rule_ids


def test_open_without_with_does_not_match_inside_async_with(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "async def f(resource):\n"
        "    async with resource:\n"
        "        return open('file.txt')\n",
    )

    assert "SEC-006" not in rule_ids
