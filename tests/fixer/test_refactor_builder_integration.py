from astroid import parse

from astanalyzer.engine import ModuleNode, ProjectNode
from astanalyzer.refactor import refactor_builder


def test_refactor_builder_renames_function_in_definition_file(tmp_path):
    code = (
        "def MyFunction():\n"
        "    return 1\n\n"
        "x = MyFunction()\n"
    )
    source = tmp_path / "a.py"
    source.write_text(code, encoding="utf-8")

    tree = parse(code, module_name=str(source))
    tree.file = str(source)
    tree.file_content = code

    fn = next(tree.get_children())

    project = ProjectNode()
    project.root_dir = tmp_path
    project.add_module(ModuleNode(filename=str(source), ast_root=tree))

    result = (
        refactor_builder()
        .rename_function_project_wide()
        .because("Use snake_case")
        .build(
            node=fn,
            module=project.modules[0],
            project=project,
            project_root=tmp_path,
        )
    )

    assert len(result) == 1
    assert "def my_function(" in result[0].suggestion
    assert "x = my_function()" in result[0].suggestion

from astroid import parse

from astanalyzer.engine import ModuleNode, ProjectNode
from astanalyzer.refactor import refactor_builder


def test_refactor_builder_renames_imported_function_usage(tmp_path):
    a_code = "def MyFunction():\n    return 1\n"
    b_code = "from a import MyFunction\n\nx = MyFunction()\n"

    a_path = tmp_path / "a.py"
    b_path = tmp_path / "b.py"
    a_path.write_text(a_code, encoding="utf-8")
    b_path.write_text(b_code, encoding="utf-8")

    a_tree = parse(a_code, module_name=str(a_path))
    a_tree.file = str(a_path)
    a_tree.file_content = a_code

    b_tree = parse(b_code, module_name=str(b_path))
    b_tree.file = str(b_path)
    b_tree.file_content = b_code

    fn = next(a_tree.get_children())

    project = ProjectNode()
    project.root_dir = tmp_path
    project.add_module(ModuleNode(filename=str(a_path), ast_root=a_tree))
    project.add_module(ModuleNode(filename=str(b_path), ast_root=b_tree))

    result = (
        refactor_builder()
        .rename_function_project_wide()
        .because("Use snake_case")
        .build(
            node=fn,
            module=project.modules[0],
            project=project,
            project_root=tmp_path,
        )
    )

    assert len(result) == 2

    suggestions = {p.filename: p.suggestion for p in result}
    assert "def my_function(" in suggestions[str(a_path)]
    assert "from a import my_function" in suggestions[str(b_path)]
    assert "x = my_function()" in suggestions[str(b_path)]

from astroid import parse

from astanalyzer.engine import ModuleNode, ProjectNode
from astanalyzer.refactor import refactor_builder


def test_refactor_builder_renames_class_project_wide(tmp_path):
    code = (
        "class my_class:\n"
        "    pass\n\n"
        "x = my_class()\n"
    )
    source = tmp_path / "a.py"
    source.write_text(code, encoding="utf-8")

    tree = parse(code, module_name=str(source))
    tree.file = str(source)
    tree.file_content = code

    cls = next(tree.get_children())

    project = ProjectNode()
    project.root_dir = tmp_path
    project.add_module(ModuleNode(filename=str(source), ast_root=tree))

    result = (
        refactor_builder()
        .rename_class_project_wide()
        .because("Use PascalCase")
        .build(
            node=cls,
            module=project.modules[0],
            project=project,
            project_root=tmp_path,
        )
    )

    assert len(result) == 1
    assert "class MyClass" in result[0].suggestion
    assert "x = MyClass()" in result[0].suggestion

from astroid import parse

from astanalyzer.engine import ModuleNode, ProjectNode
from astanalyzer.refactor import refactor_builder


def test_refactor_builder_renames_constant_project_wide(tmp_path):
    code = (
        "myConst = 1\n"
        "x = myConst + 1\n"
    )
    source = tmp_path / "a.py"
    source.write_text(code, encoding="utf-8")

    tree = parse(code, module_name=str(source))
    tree.file = str(source)
    tree.file_content = code

    assign = next(tree.get_children())

    project = ProjectNode()
    project.root_dir = tmp_path
    project.add_module(ModuleNode(filename=str(source), ast_root=tree))

    result = (
        refactor_builder()
        .rename_constant_project_wide()
        .because("Use UPPER_SNAKE_CASE")
        .build(
            node=assign,
            module=project.modules[0],
            project=project,
            project_root=tmp_path,
        )
    )

    assert len(result) == 1
    assert "MY_CONST = 1" in result[0].suggestion
    assert "x = MY_CONST + 1" in result[0].suggestion
