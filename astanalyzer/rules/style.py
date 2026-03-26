"""
Style rules for astanalyzer.

This module contains a collection of static analysis rules focused on
code style, readability, and basic maintainability patterns in Python code.

The rules are defined using the AstroDSL matcher DSL and are designed to:
- detect stylistic inconsistencies (naming conventions, formatting issues)
- highlight readability problems (deep nesting, long lines, missing docstrings)
- suggest lightweight, mostly safe automatic fixes
- optionally provide refactoring actions (project-wide renames, structural hints)

Each rule:
- extends the `Rule` base class
- defines one or more `matchers` (DSL-based AST queries)
- optionally defines `fixer_builders` (line-based fixes)
- may define `refactor_builder` actions for project-wide transformations

The rules operate on top of `astroid` AST nodes and rely on:
- matcher DSL (`match(...)`)
- helper predicates (e.g. `missing_docstring`, `line_too_long`)
- fixer DSL (`fix_builder()`)
- refactor DSL (`refactor_builder()`)

Design principles:
- prefer simple, readable DSL over complex imperative logic
- keep rules declarative whenever possible
- avoid unsafe automatic changes unless explicitly requested
- separate detection (scan) from modification (fix/refactor)

This module intentionally groups style-related rules in one place,
but the architecture allows splitting them into multiple modules
(e.g. naming.py, formatting.py, documentation.py) in the future.

Note:
Some rules may include partial or advisory fixes only, especially when
full refactoring would require semantic analysis beyond AST level.
"""

from __future__ import annotations

from ..enums import NodeType, RuleCategory, Severity
from ..fixer import fix
from ..refactor import refactor_builder
from ..matcher import match
from ..rule import Rule
from ..tools import has_trailing_whitespace


class EmptyBlock(Rule):
    id = "BLK-001"
    title = "Empty block"
    severity = Severity.WARNING
    category = RuleCategory.STYLE
    node_type = {
        NodeType.IF,
        NodeType.FOR,
        NodeType.WHILE,
        NodeType.TRY,
        NodeType.WITH,
        NodeType.EXCEPT_HANDLER,
    }

    BLOCK_TYPES = ("If", "For", "While", "Try", "With", "ExceptHandler")

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("|".join(self.BLOCK_TYPES)).empty_block()
        ]
        self.fixer_builders = [
            fix()
            .insert_at_body_start("# TODO: implement block logic")
            .because("Empty block should contain real logic or be removed."),
            fix()
            .delete_node()
            .because("Empty block can be removed."),
        ]


class RedundantIfElseReturn(Rule):
    id = "COND-002"
    title = "Redundant else after terminal branches"
    severity = Severity.INFO
    category = RuleCategory.STYLE
    node_type = NodeType.IF

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("If").redundant_else_after_terminal()
        ]
        self.fixer_builders = [
            fix()
            .remove_block_header("orelse")
            .unindent_block("orelse", spaces=4)
            .because("Else block is redundant after a terminal branch."),
        ]


class MultipleReturnsInFunction(Rule):
    id = "FUNC-001"
    title = "Function with multiple return statements"
    severity = Severity.INFO
    category = RuleCategory.STYLE
    node_type = NodeType.FUNCTION_DEF

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("FunctionDef").multiple_returns()
        ]
        self.fixer_builders = [
            fix()
            .comment_on_function(
                "# TODO: Consider refactoring to a single return path if it improves readability."
            )
            .because("Function contains multiple return statements."),
        ]


class LineTooLong(Rule):
    id = "STYLE-017"
    title = "Line too long"
    severity = Severity.INFO
    category = RuleCategory.STYLE
    node_type = NodeType.MODULE

    MAX_LEN = 100

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Module").line_too_long(self.MAX_LEN)
        ]
        self.fixer_builders = [
            fix()
            .comment_before("TODO: split long lines or use shorter names.")
            .because("Module contains lines longer than the configured limit."),
        ]


class FunctionNameNotSnakeCase(Rule):
    id = "NAM-018"
    title = "Function name not in snake_case"
    severity = Severity.INFO
    category = RuleCategory.STYLE
    node_type = NodeType.FUNCTION_DEF

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("FunctionDef").name_not_snake()
        ]
        self.fixer_builders = [
            refactor_builder()
            .rename_function_project_wide()
            .because("Function names should follow snake_case."),
        ]


class ClassNameNotPascalCase(Rule):
    id = "NAM-019"
    title = "Class name not in PascalCase"
    severity = Severity.INFO
    category = RuleCategory.STYLE
    node_type = NodeType.CLASS_DEF

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("ClassDef").name_not_pascal()
        ]
        self.fixer_builders = [
            refactor_builder()
            .rename_class_project_wide()
            .because("Class names should follow PascalCase."),
        ]


class ConstantNotUppercase(Rule):
    id = "NAM-020"
    title = "Constant not in UPPER_SNAKE_CASE"
    severity = Severity.INFO
    category = RuleCategory.STYLE
    node_type = {NodeType.ASSIGN, NodeType.ANN_ASSIGN}

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Assign|AnnAssign").constant_name_not_upper()
        ]
        self.fixer_builders = [
            refactor_builder()
            .rename_constant_project_wide()
            .because("Constants should follow UPPER_SNAKE_CASE."),
        ]


class TrailingWhitespace(Rule):
    id = "STYLE-021"
    title = "Trailing whitespace"
    severity = Severity.INFO
    category = RuleCategory.STYLE
    node_type = NodeType.MODULE

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Module").where("__custom_condition__", has_trailing_whitespace)
        ]
        self.fixer_builders = [
            fix()
            .strip_trailing_whitespace()
            .because("Trailing whitespace should be removed."),
        ]


class MissingBlankLineBetweenFunctions(Rule):
    id = "STYLE-022"
    title = "Missing blank line(s) between definitions"
    severity = Severity.INFO
    category = RuleCategory.STYLE
    node_type = NodeType.FUNCTION_DEF

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("FunctionDef").missing_blank_before()
        ]
        self.fixer_builders = [
            fix()
            .insert_blank_line_before()
            .because("Definitions should be separated by a blank line."),
        ]


class MissingDocstringForFunction(Rule):
    id = "STYLE-002"
    title = "Missing docstring for function"
    severity = Severity.WARNING
    category = RuleCategory.STYLE
    node_type = NodeType.FUNCTION_DEF

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("FunctionDef").missing_docstring()
        ]
        self.fixer_builders = [
            fix()
            .add_docstring('"""TODO: Describe the function, its parameters and return value."""')
            .because("Function is missing a docstring."),
        ]


class MissingDocstringForClass(Rule):
    id = "STYLE-003"
    title = "Missing docstring for class"
    severity = Severity.WARNING
    category = RuleCategory.STYLE
    node_type = NodeType.CLASS_DEF

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("ClassDef").missing_docstring()
        ]
        self.fixer_builders = [
            fix()
            .add_docstring('"""TODO: Describe the class purpose, attributes, and usage."""')
            .because("Class is missing a docstring."),
        ]


class MissingDocstringForModule(Rule):
    id = "STYLE-023"
    title = "Missing docstring for module"
    severity = Severity.WARNING
    category = RuleCategory.STYLE
    node_type = NodeType.MODULE

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Module").missing_module_docstring()
        ]
        self.fixer_builders = [
            fix()
            .add_module_docstring('"""TODO: Describe the module purpose, contents, and usage."""')
            .because("Module is missing a docstring."),
        ]


__all__ = [
    "EmptyBlock",
    "RedundantIfElseReturn",
    "MultipleReturnsInFunction",
    "LineTooLong",
    "FunctionNameNotSnakeCase",
    "ClassNameNotPascalCase",
    "ConstantNotUppercase",
    "TrailingWhitespace",
    "MissingBlankLineBetweenFunctions",
    "MissingDocstringForFunction",
    "MissingDocstringForClass",
    "MissingDocstringForModule",
]
