from astroid import parse

from astanalyzer.engine import load_project, run_rules_on_project_report, attach_tree_metadata
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

    report, scan = run_rules_on_project_report(project, build_plans=True, build_fixes=False)
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