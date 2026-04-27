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
    """
    This block contains no executable logic.

    Empty control structures (if, for, while, try, with, except) reduce code clarity
    and may indicate unfinished implementation or redundant code.

    Consider adding meaningful logic or removing the block entirely.
    """
    id = "STYLE-001"
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
            .add_review_note_and_ignore(
                "STYLE-001",
                "TODO: implement block logic or remove this empty block.",
            )
            .because(
                "Add a review note and suppress this advisory style finding "
                "until the empty block is manually implemented or removed."
            ),
            fix()
            .delete_node()
            .because("Empty block can be removed."),
        ]


class RedundantIfElseReturn(Rule):
    """
    Redundant 'else' block after a terminal statement.

    When an 'if' branch ends with a terminal statement (e.g. return, raise, break),
    the 'else' block is unnecessary because control flow will not continue past it.

    Removing the 'else' and unindenting its contents simplifies the code and improves readability.
    """
    id = "STYLE-002"
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
    """
    Function contains multiple return statements.

    Having multiple return points can make control flow harder to follow,
    especially in more complex functions. In some cases, consolidating returns
    into a single exit point can improve readability and maintainability.

    However, multiple returns may be acceptable if they keep the code simpler
    and more understandable.
    """
    id = "STYLE-003"
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
            .add_review_note_and_ignore(
                "STYLE-003",
                "Function contains multiple return statements. Consider whether a single exit point would improve readability.",
            )
            .because(
                "Add a review note and suppress this advisory style finding "
                "until the function is manually reviewed."
            )
        ]
        

class LineTooLong(Rule):
    """
    Line exceeds the recommended maximum length.

    Long lines reduce readability, especially in diffs, code reviews, and
    side-by-side views. Keeping lines within a reasonable limit improves
    clarity and consistency across the codebase.

    Consider splitting the line or using shorter expressions.
    """
    id = "STYLE-004"
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
            .add_review_note_and_ignore(
                "STYLE-004",
                "Line exceeds the configured length. Consider splitting the expression or extracting intermediate variables.",
            )
            .because(
                "Add a review note and suppress this advisory formatting finding "
                "until the line is manually reformatted."
            )
        ]


class FunctionNameNotSnakeCase(Rule):
    """
    Function name does not follow snake_case convention.

    In Python, function names should use snake_case (lowercase words separated
    by underscores) according to PEP 8. Consistent naming improves readability,
    predictability, and collaboration across the codebase.

    Consider renaming the function to follow snake_case.
    """
    id = "STYLE-005"
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
    """
    Class name does not follow PascalCase convention.

    In Python, class names should use PascalCase (also known as CapWords),
    where each word starts with a capital letter. This follows PEP 8 and
    helps distinguish classes from functions and variables.

    Consider renaming the class to follow PascalCase.
    """
    id = "STYLE-006"
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
    """
    Constant name does not follow UPPER_SNAKE_CASE convention.

    In Python, constants should be written in UPPER_SNAKE_CASE according to
    PEP 8. This makes them easily distinguishable from variables and signals
    that their value is intended to remain unchanged.

    Consider renaming the constant to follow this convention.
    """
    id = "STYLE-007"
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
    """
    Line contains trailing whitespace.

    Trailing whitespace has no functional meaning and can introduce unnecessary
    noise in diffs, version control, and code reviews. It is generally considered
    good practice to remove it.

    Consider removing trailing whitespace from the affected lines.
    """
    id = "STYLE-008"
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
    """
    Missing blank line before function definition.

    According to PEP 8, top-level function definitions should be separated
    by blank lines to improve readability and visual structure of the code.

    Consider adding a blank line before this function.
    """
    id = "STYLE-009"
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
    """
    Function is missing a docstring.

    Docstrings describe the purpose, parameters, and return values of a function.
    Without them, the code is harder to understand, use, and maintain—especially
    for other developers or future readers.

    Consider adding a clear and concise docstring.
    """
    id = "STYLE-010"
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
    """
    Class is missing a docstring.

    A class docstring should describe its purpose, responsibilities, and how it
    is intended to be used. Without it, understanding the role of the class within
    the system becomes harder, especially in larger codebases.

    Consider adding a clear and concise docstring.
    """
    id = "STYLE-011"
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
    """
    Module is missing a docstring.

    A module docstring provides a high-level overview of the file’s purpose,
    its main components, and how it should be used. Without it, understanding
    the role of the module within the project becomes more difficult.

    Consider adding a clear and concise module-level docstring.
    """
    id = "STYLE-012"
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
