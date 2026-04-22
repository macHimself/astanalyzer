def test_use_of_eval_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "eval('1 + 1')\n",
    )

    assert "SEC-001" in rule_ids


def test_exec_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "exec('x = 1')\n",
    )

    assert "SEC-001" in rule_ids


def test_eval_literal_parsing_candidate_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "eval('[1, 2, 3]')\n",
    )

    assert "SEC-002" in rule_ids


def test_eval_literal_parsing_candidate_not_detected_for_variable_input(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "data = input()\n"
        "eval(data)\n",
    )

    assert "SEC-002" not in rule_ids


def test_use_of_os_system_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "import os\n"
        "os.system('ls')\n",
    )

    assert "SEC-003" in rule_ids


def test_use_of_os_popen_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "import os\n"
        "os.popen('ls')\n",
    )

    assert "SEC-003" in rule_ids


def test_hardcoded_password_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "password = 'secret123'\n",
    )

    assert "SEC-004" in rule_ids


def test_hardcoded_token_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "api_token = 'abc123'\n",
    )

    assert "SEC-004" in rule_ids


def test_hardcoded_password_not_detected_for_non_string(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "password = 12345\n",
    )

    assert "SEC-004" not in rule_ids


def test_insecure_random_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "import random\n"
        "x = random.randint(1, 10)\n",
    )

    assert "SEC-005" in rule_ids


def test_insecure_random_choice_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "import random\n"
        "x = random.choice([1, 2, 3])\n",
    )

    assert "SEC-005" in rule_ids


def test_insecure_random_not_detected_for_secrets(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "import secrets\n"
        "x = secrets.randbelow(10)\n",
    )

    assert "SEC-005" not in rule_ids


def test_open_without_with_matches(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "f = open('x.txt')\n",
    )

    assert "SEC-006" in rule_ids


def test_open_inside_with_not_detected(scan_rule_ids):
    rule_ids = scan_rule_ids(
        "with open('x.txt') as f:\n"
        "    data = f.read()\n",
    )

    assert "SEC-006" not in rule_ids
