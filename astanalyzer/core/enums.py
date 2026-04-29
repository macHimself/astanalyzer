"""
Shared enum definitions used across the astanalyzer project.

This module defines common classification types for findings, rules, fixes,
security impact levels, and supported AST node kinds. These enums provide
a consistent vocabulary for rule definitions, reports, fix generation,
and internal matching logic.
"""

from enum import StrEnum, IntEnum

class Severity(StrEnum):
    """Severity level assigned to a rule finding."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class RuleCategory(StrEnum):
    """High-level category describing the type of rule or finding."""
    STYLE = "style"
    COMPLEXITY = "complexity"
    SECURITY = "security"
    PERFORMANCE = "performance"
    BEST_PRACTICE = "best_practice"
    DEAD_CODE = "dead_code"
    SEMANTIC = "semantic"
    RESOURCE = "resource"

class FixType(StrEnum):
    """Type of code modification represented by a fix action."""
    INSERT = "insert"
    REPLACE = "replace"
    DELETE = "delete"
    COMMENT = "comment"

class SecurityImpact(IntEnum):
    """Ordered security impact level used for prioritizing security findings."""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class NodeType(StrEnum):
    """Supported AST node types used by rules and matcher definitions."""
    # ===== Module / definitions =====
    MODULE = "Module"
    FUNCTION_DEF = "FunctionDef"
    ASYNC_FUNCTION_DEF = "AsyncFunctionDef"
    CLASS_DEF = "ClassDef"
    LAMBDA = "Lambda"

    # ===== Control flow =====
    IF = "If"
    FOR = "For"
    ASYNC_FOR = "AsyncFor"
    WHILE = "While"
    TRY = "Try"
    TRY_STAR = "TryStar"
    WITH = "With"
    ASYNC_WITH = "AsyncWith"
    MATCH = "Match"
    MATCH_CASE = "MatchCase"
    EXCEPT_HANDLER = "ExceptHandler"

    # ===== Assignments =====
    ASSIGN = "Assign"
    ANN_ASSIGN = "AnnAssign"
    AUG_ASSIGN = "AugAssign"
    NAMED_EXPR = "NamedExpr"

    # ===== Expressions =====
    CALL = "Call"
    ATTRIBUTE = "Attribute"
    NAME = "Name"
    CONST = "Const"
    BIN_OP = "BinOp"
    BOOL_OP = "BoolOp"
    UNARY_OP = "UnaryOp"
    COMPARE = "Compare"
    SUBSCRIPT = "Subscript"
    SLICE = "Slice"
    STARRED = "Starred"

    # ===== Imports =====
    IMPORT = "Import"
    IMPORT_FROM = "ImportFrom"

    # ===== Flow termination =====
    RETURN = "Return"
    RAISE = "Raise"
    BREAK = "Break"
    CONTINUE = "Continue"
    PASS = "Pass"
    YIELD = "Yield"
    YIELD_FROM = "YieldFrom"

    # ===== Collections =====
    LIST = "List"
    TUPLE = "Tuple"
    SET = "Set"
    DICT = "Dict"

    # ===== Comprehensions =====
    EXPR = "Expr"
    LIST_COMP = "ListComp"
    SET_COMP = "SetComp"
    DICT_COMP = "DictComp"
    GENERATOR_EXP = "GeneratorExp"   
