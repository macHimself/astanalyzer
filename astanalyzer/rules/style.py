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
    WHAT:
    Detects control-flow blocks that contain no executable logic.

    WHY:
    Empty blocks make the code harder to understand because they suggest that
    some behaviour should exist but has not been implemented. They may indicate
    unfinished work, leftover scaffolding, or redundant control flow.

    WHEN:
    This is relevant for if, for, while, try, with, and except blocks in normal
    source code. It may be intentional for placeholders, abstract examples, or
    temporary development code, but such intent should be explicit.

    HOW:
    Add the missing logic if the block is unfinished, or remove the block if it is
    redundant. If the empty block is intentional, add a clear review note or
    suppress the advisory finding.
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
    WHAT:
    Detects else blocks that follow an if branch ending with a terminal statement
    such as return, raise, break, or continue.

    WHY:
    When the if branch terminates control flow, the else block is not needed.
    Removing it reduces indentation and makes the remaining execution path easier
    to read.

    WHEN:
    This is relevant when the else block only exists because of unnecessary
    nesting. It may be less useful when the explicit else improves symmetry or
    makes two alternative branches clearer.

    HOW:
    Remove the else header and unindent its body. Keep the explicit else only when
    it makes the control-flow alternatives easier to understand.
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
    WHAT:
    Detects functions that contain multiple return statements.

    WHY:
    Multiple return points can make control flow harder to follow, especially in
    long or complex functions. They may make it less obvious which paths produce
    which result.

    WHEN:
    This is mainly relevant for complex functions with branching logic. Multiple
    returns are often acceptable when used as guard clauses or when they make the
    function simpler and flatter.

    HOW:
    Review whether a single exit point would improve clarity. If multiple returns
    make the function easier to understand, keep them and suppress the advisory
    finding.
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
    WHAT:
    Detects lines that exceed the configured maximum line length.

    WHY:
    Very long lines are harder to read in diffs, code reviews, terminal editors,
    and side-by-side views. They can also hide complex expressions that would be
    clearer if split into smaller parts.

    WHEN:
    This is relevant for most source files and shared codebases. It may be
    acceptable for long URLs, generated code, data literals, or strings where
    splitting would reduce clarity.

    HOW:
    Split long expressions across multiple lines, extract intermediate variables,
    or reformat argument lists. If the long line is intentional and clearer as-is,
    suppress the advisory finding.
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
    WHAT:
    Detects function names that do not follow the snake_case naming convention.

    WHY:
    Consistent naming makes Python code easier to scan and understand. Following
    snake_case helps distinguish functions from classes and keeps the code aligned
    with common Python style conventions.

    WHEN:
    This is relevant for project-owned Python functions. It may be intentional for
    framework hooks, external API compatibility, generated code, or functions that
    must match names defined outside the project.

    HOW:
    Rename the function to snake_case and update its references. If the name is
    required by an external interface, keep it and suppress the finding.
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
    WHAT:
    Detects class names that do not follow the PascalCase / CapWords convention.

    WHY:
    Consistent class naming helps readers immediately distinguish classes from
    functions, variables, and modules. It also keeps the code aligned with common
    Python style conventions.

    WHEN:
    This is relevant for project-owned classes. It may be intentional for generated
    code, compatibility layers, framework-specific names, or classes that mirror
    external schemas.

    HOW:
    Rename the class to PascalCase and update references across the project. If
    the name is required externally, keep it and suppress the finding.
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
    WHAT:
    Detects constants whose names do not follow the UPPER_SNAKE_CASE convention.

    WHY:
    Uppercase constant names signal that a value is intended to be stable and not
    modified during normal execution. Inconsistent naming makes it harder to
    distinguish constants from ordinary variables.

    WHEN:
    This is relevant for module-level values that are intended to behave as
    constants. It may be a false positive for normal variables, generated code, or
    values that are intentionally mutable or reassigned.

    HOW:
    Rename true constants to UPPER_SNAKE_CASE and update references. If the value
    is not actually a constant, rename or restructure it to reflect its real role.
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
    WHAT:
    Detects whitespace at the end of a line.

    WHY:
    Trailing whitespace has no semantic value and creates unnecessary noise in
    diffs, version control history, and code reviews. It can also conflict with
    formatting tools or editor settings.

    WHEN:
    This is relevant in almost all source files. It is rarely intentional, except
    in special text fixtures where exact whitespace is meaningful.

    HOW:
    Remove trailing whitespace from the affected lines. If exact trailing spaces
    are required in a fixture or generated file, exclude or suppress the finding.
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
    WHAT:
    Detects function definitions that are not visually separated by the expected
    blank line spacing.

    WHY:
    Blank lines make source files easier to scan by visually separating independent
    definitions. Missing separation can make functions appear connected even when
    they are unrelated.

    WHEN:
    This is relevant for top-level functions and class methods where consistent
    layout improves readability. It may be less relevant in generated code or very
    compact examples.

    HOW:
    Insert the required blank line before the function definition. If the compact
    layout is intentional, suppress the advisory finding.
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
    WHAT:
    Detects functions that do not define a docstring.

    WHY:
    A function docstring explains the purpose of the function, important parameters,
    return values, side effects, and usage constraints. Without it, the function is
    harder to use correctly and maintain later.

    WHEN:
    This is most relevant for public APIs, complex functions, reusable utilities,
    and functions with non-obvious behaviour. It may be unnecessary for very small
    private helpers or tests where the intent is already clear.

    HOW:
    Add a concise docstring that explains what the function does, when to use it,
    and any important parameters, return values, exceptions, or side effects.
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
    WHAT:
    Detects classes that do not define a docstring.

    WHY:
    A class docstring explains the role, responsibility, and intended usage of the
    class. Without it, readers must infer the design from implementation details,
    which becomes harder in larger codebases.

    WHEN:
    This is most relevant for public classes, domain models, services, rule
    classes, and classes with meaningful state or behaviour. It may be unnecessary
    for tiny internal helper classes or generated code.

    HOW:
    Add a concise class docstring describing the class purpose, main
    responsibilities, important attributes, and typical usage.
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
    WHAT:
    Detects modules that do not define a module-level docstring.

    WHY:
    A module docstring provides a high-level explanation of the file's purpose,
    main contents, and role in the project. Without it, readers have to inspect
    individual functions and classes before understanding the module.

    WHEN:
    This is most relevant for modules containing public functionality, rule groups,
    core engine components, or non-trivial implementation logic. It may be less
    important for generated files, tiny scripts, or package marker files.

    HOW:
    Add a module-level docstring that summarises the module purpose, the main
    concepts it contains, and any important usage or design notes.
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
