from astanalyzer.refactor import RefactorBuilder, refactor_builder
from astanalyzer.utils import to_pascal_case, to_snake_case, to_upper_snake_case

__all__ = [
    "RefactorBuilder",
    "refactor_builder",
    "to_snake_case",
    "to_pascal_case",
    "to_upper_snake_case",
]

def test_to_snake_case():
    assert to_snake_case("MyFunction") == "my_function"
    assert to_snake_case("myFunction") == "my_function"


def test_to_pascal_case():
    assert to_pascal_case("my_class") == "MyClass"
    assert to_pascal_case("my class") == "MyClass"


def test_to_upper_snake_case():
    assert to_upper_snake_case("myConst") == "MY_CONST"
    assert to_upper_snake_case("my const") == "MY_CONST"


def test_refactor_builder_to_dict_for_function_rename():
    builder = (
        refactor_builder()
        .rename_function_project_wide()
        .because("Use snake_case naming.")
    )

    data = builder.to_dict()

    assert data["title"] == "Proposed refactor"
    assert data["reason"] == "Use snake_case naming."
    assert data["dsl"]["actions"] == [{"op": "rename_function_project_wide"}]


def test_refactor_builder_collects_multiple_operations():
    builder = RefactorBuilder()
    builder.rename_function_project_wide().rename_class_project_wide()

    assert builder.operations == [
        {"op": "rename_function_project_wide"},
        {"op": "rename_class_project_wide"},
    ]
