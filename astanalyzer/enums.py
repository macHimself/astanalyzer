from enum import StrEnum, IntEnum

class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class RuleCategory(StrEnum):
    STYLE = "style"
    COMPLEXITY = "complexity"
    SECURITY = "security"
    PERFORMANCE = "performance"
    BEST_PRACTICE = "best_practice"
    DEAD_CODE = "dead_code"
    SEMANTIC = "semantic"
    RESOURCE = "resource"

class FixType(StrEnum):
    INSERT = "insert"
    REPLACE = "replace"
    DELETE = "delete"
    COMMENT = "comment"

class SecurityImpact(IntEnum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class NodeType(StrEnum):
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

    