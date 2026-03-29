from astroid import parse

from astanalyzer.engine import attach_tree_metadata, load_project, run_rules_on_project_report
from astanalyzer.ignore_rules import _parse_ignore_rule_ids, is_ignored_for_node


def test_ignore_inline_rule_suppresses_finding(tmp_path):
    source = tmp_path / "a.py"
    source.write_text(
        "def BadName():  # astanalyzer: ignore NAM-018\n"
        "    return 1\n",
        encoding="utf-8",
    )

    project = load_project([str(source)])
    project.root_dir = tmp_path

    _, scan = run_rules_on_project_report(project, build_plans=True, build_fixes=False)
    rule_ids = {f["rule_id"] for f in scan["findings"]}

    assert "NAM-018" not in rule_ids


def test_parse_ignore_rule_ids_inline():
    ids = _parse_ignore_rule_ids("def BadName():  # astanalyzer: ignore NAM-018")
    assert "NAM-018" in ids


def test_is_ignored_for_functiondef_inline_comment():
    code = (
        "def BadName():  # astanalyzer: ignore NAM-018\n"
        "    return 1\n"
    )
    tree = parse(code, module_name="a.py")
    attach_tree_metadata(tree, "a.py", code)

    fn = next(tree.get_children())

    assert is_ignored_for_node("NAM-018", fn) is True


def test_ignore_next_suppresses_finding(scan_rule_ids):
    source = """
# astanalyzer: ignore-next STYLE-003
def foo():
    if True:
        return 1
    return 2
"""

    rule_ids = scan_rule_ids(source)

    assert "STYLE-003" not in rule_ids


def test_rule_detected_without_ignore(scan_rule_ids):
    source = """
def foo():
    if True:
        return 1
    return 2
"""

    rule_ids = scan_rule_ids(source)

    assert "STYLE-003" in rule_ids


def test_inline_ignore_same_line(scan_rule_ids):
    source = """
x = eval("1 + 1")  # astanalyzer: ignore SEC-001
"""

    rule_ids = scan_rule_ids(source)

    assert "SEC-001" not in rule_ids


def test_block_disable_enable(scan_rule_ids):
    source = """
# astanalyzer: disable STYLE-003

def foo():
    if True:
        return 1
    return 2

# astanalyzer: enable STYLE-003

def bar():
    if True:
        return 1
    return 2
"""

    rule_ids = scan_rule_ids(source)

    assert rule_ids.count("STYLE-003") == 1


def test_ignore_all_rules(scan_rule_ids):
    source = """
# astanalyzer: ignore-next
def foo():
    if True:
        return 1
    return 2
"""

    rule_ids = scan_rule_ids(source)

    assert "STYLE-003" not in rule_ids


def test_parse_ignore_multiple_rules():
    ids = _parse_ignore_rule_ids("# astanalyzer: ignore-next STYLE-003, STYLE-003")
    assert "STYLE-003" in ids
    assert "STYLE-003" in ids


def test_is_ignored_for_node_with_multiple_rules():
    code = (
        "# astanalyzer: ignore-next STYLE-003, STYLE-003\n"
        "def foo():\n"
        "    if True:\n"
        "        return 1\n"
        "    return 2\n"
    )
    tree = parse(code, module_name="a.py")
    attach_tree_metadata(tree, "a.py", code)

    fn = next(tree.get_children())

    assert is_ignored_for_node("STYLE-003", fn) is True
    assert is_ignored_for_node("STYLE-003", fn) is True
    assert is_ignored_for_node("SEC-001", fn) is False


def test_sec_001_detected_without_ignore(scan_rule_ids):
    source = '''
x = eval("1 + 1")
'''
    rule_ids = scan_rule_ids(source)

    assert "SEC-001" in rule_ids


def test_sec_001_suppressed_with_inline_ignore(scan_rule_ids):
    source = '''
x = eval("1 + 1")  # astanalyzer: ignore SEC-001
'''
    rule_ids = scan_rule_ids(source)

    assert "SEC-001" not in rule_ids


def test_multiple_rules_detected_without_ignore(scan_rule_ids):
    source = '''
def foo():
    if True:
        return 1
    return 2
'''
    rule_ids = scan_rule_ids(source)

    assert "STYLE-003" in rule_ids
    assert "STYLE-010" in rule_ids
    assert "STYLE-012" in rule_ids


def test_multiple_rules_suppressed_with_ignore_next(scan_rule_ids):
    source = '''
# astanalyzer: ignore-next STYLE-003, STYLE-010
def foo():
    if True:
        return 1
    return 2
'''
    rule_ids = scan_rule_ids(source)

    assert "STYLE-003" not in rule_ids
    assert "STYLE-010" not in rule_ids
    assert "STYLE-012" in rule_ids