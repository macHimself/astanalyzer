from astanalyzer.engine import load_project, run_rules_on_project_report
from astanalyzer.rule_loader import import_rules_from_path
from astanalyzer.rules import load_builtin_rules


def test_import_rules_from_path_loads_custom_rule(tmp_path):
    rule_file = tmp_path / "my_rules.py"
    rule_file.write_text(
        "from astanalyzer.core.rule import Rule\n"
        "from astanalyzer.matcher import match\n"
        "from astanalyzer.core.enums import Severity, RuleCategory, NodeType\n"
        "\n"
        "class MyCustomRule(Rule):\n"
        "    id = 'CUST-001'\n"
        "    title = 'Detect foo function'\n"
        "    severity = Severity.INFO\n"
        "    category = RuleCategory.STYLE\n"
        "    node_type = NodeType.FUNCTION_DEF\n"
        "\n"
        "    def __init__(self):\n"
        "        super().__init__()\n"
        "        self.matchers = [\n"
        "            match('FunctionDef').where('name', 'foo')\n"
        "        ]\n",
        encoding="utf-8",
    )

    source = tmp_path / "sample.py"
    source.write_text(
        "def foo():\n"
        "    return 1\n",
        encoding="utf-8",
    )

    load_builtin_rules()
    imported = import_rules_from_path(rule_file)

    assert imported == [rule_file.resolve()]

    project = load_project([str(source)])
    project.root_dir = tmp_path

    _, scan = run_rules_on_project_report(
        project,
        build_plans=True,
        build_fixes=False,
    )

    rule_ids = [f["rule_id"] for f in scan["findings"]]
    assert "CUST-001" in rule_ids
