from astroid import parse
from astanalyzer.fixer import fix


def test_add_docstring_builds_fix():
    code = """
def hello():
    return 1
""".lstrip()

    tree = parse(code, module_name="x.py")
    tree.file = "x.py"
    tree.file_content = code
    fn = next(tree.get_children())

    proposal = (
        fix()
        .add_docstring('"""TODO"""')
        .because("Missing docstring")
        .build(fn)
    )

    assert '"""TODO"""' in proposal.suggestion
    assert proposal.reason == "Missing docstring"
