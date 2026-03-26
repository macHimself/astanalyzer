import pytest
from astanalyzer.engine import load_project, run_rules_on_project_report


def scan_rule_ids(tmp_path, filename: str, code: str) -> list[str]:
    source = tmp_path / filename
    source.write_text(code, encoding="utf-8")

    project = load_project([str(source)])
    project.root_dir = tmp_path

    _, scan = run_rules_on_project_report(
        project,
        build_plans=True,
        build_fixes=False,
    )

    return [f["rule_id"] for f in scan["findings"]]


def test_missing_docstring_detected(tmp_path):
    rule_ids = scan_rule_ids(
        tmp_path,
        "a.py",
        "def foo():\n"
        "    return 1\n",
    )

    assert "STYLE-002" in rule_ids


def test_missing_docstring_not_detected_when_present(tmp_path):
    rule_ids = scan_rule_ids(
        tmp_path,
        "a.py",
        'def foo():\n'
        '    """This is a docstring."""\n'
        '    return 1\n',
    )

    assert "STYLE-002" not in rule_ids


def test_missing_class_docstring_detected(tmp_path):
    rule_ids = scan_rule_ids(
        tmp_path,
        "a.py",
        "class MyClass:\n"
        "    pass\n",
    )

    assert "STYLE-003" in rule_ids


def test_missing_module_docstring_detected(tmp_path):
    rule_ids = scan_rule_ids(
        tmp_path,
        "a.py",
        "x = 1\n",
    )

    assert "STYLE-023" in rule_ids


def test_function_name_not_snake_case_detected(tmp_path):
    rule_ids = scan_rule_ids(
        tmp_path,
        "a.py",
        "def BadName():\n"
        "    pass\n",
    )

    assert "NAM-018" in rule_ids


def test_function_name_snake_case_not_detected(tmp_path):
    rule_ids = scan_rule_ids(
        tmp_path,
        "a.py",
        "def good_name():\n"
        "    pass\n",
    )

    assert "NAM-018" not in rule_ids


def test_class_name_not_pascal_case_detected(tmp_path):
    rule_ids = scan_rule_ids(
        tmp_path,
        "a.py",
        "class bad_name:\n"
        "    pass\n",
    )

    assert "NAM-019" in rule_ids


def test_class_name_pascal_case_not_detected(tmp_path):
    rule_ids = scan_rule_ids(
        tmp_path,
        "a.py",
        "class GoodName:\n"
        "    pass\n",
    )

    assert "NAM-019" not in rule_ids


def test_constant_not_uppercase_detected(tmp_path):
    rule_ids = scan_rule_ids(
        tmp_path,
        "a.py",
        "my_constant = 1\n",
    )

    assert "NAM-020" in rule_ids


def test_constant_uppercase_not_detected(tmp_path):
    rule_ids = scan_rule_ids(
        tmp_path,
        "a.py",
        "MY_CONSTANT = 1\n",
    )

    assert "NAM-020" not in rule_ids


def test_trailing_whitespace_detected(tmp_path):
    rule_ids = scan_rule_ids(
        tmp_path,
        "a.py",
        "x = 1   \n",
    )

    assert "STYLE-021" in rule_ids


def test_missing_blank_line_between_functions_detected(tmp_path):
    rule_ids = scan_rule_ids(
        tmp_path,
        "a.py",
        "def a():\n"
        "    pass\n"
        "def b():\n"
        "    pass\n",
    )

    assert "STYLE-022" in rule_ids


def test_line_too_long_detected(tmp_path):
    long_line = "x = '" + ("a" * 120) + "'\n"
    rule_ids = scan_rule_ids(
        tmp_path,
        "a.py",
        long_line,
    )

    assert "STYLE-017" in rule_ids


def test_multiple_returns_detected(tmp_path):
    rule_ids = scan_rule_ids(
        tmp_path,
        "a.py",
        "def foo(x):\n"
        "    if x:\n"
        "        return 1\n"
        "    return 2\n",
    )

    assert "FUNC-001" in rule_ids


def test_redundant_else_after_return_detected(tmp_path):
    rule_ids = scan_rule_ids(
        tmp_path,
        "a.py",
        "def foo(x):\n"
        "    if x:\n"
        "        return 1\n"
        "    else:\n"
        "        return 2\n",
    )

    assert "COND-002" in rule_ids


def test_empty_block_detected(tmp_path):
    rule_ids = scan_rule_ids(
        tmp_path,
        "a.py",
        "if True:\n"
        "    pass\n",
    )

    assert "BLK-001" in rule_ids