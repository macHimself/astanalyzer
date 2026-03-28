"""
Security and resource-management rules for astanalyzer.

This module defines static analysis rules that target insecure constructs,
risky runtime behaviour, and basic resource-management issues in Python code.

The rules focus on patterns such as:
- dynamic code execution (`eval`, `exec`)
- unsafe shell command execution (`os.system`, `os.popen`)
- possible hardcoded secrets
- insecure randomness for security-sensitive contexts
- file handling without context managers

These rules are intentionally conservative:
- some findings are warnings rather than hard errors
- some fixes are advisory comments rather than automatic rewrites
- automatic fixes are only provided where the intended transformation is
  reasonably safe and predictable

The rules operate on `astroid` AST nodes and use the matcher DSL together
with fixer DSL actions.
"""

from __future__ import annotations

from ..enums import NodeType, RuleCategory, Severity
from ..fixer import fix
from ..matcher import match
from ..rule import Rule


class UseOfEval(Rule):
    """
    Use of eval() or exec() detected.

    Dynamic code execution is unsafe, especially when handling untrusted input.
    It can lead to code injection vulnerabilities and allow attackers to execute
    arbitrary code.

    Avoid using eval() or exec(). Prefer safer alternatives such as explicit
    parsing, dispatch tables, or controlled execution mechanisms.
    """
    id = "SEC-030"
    title = "Use of eval()/exec()"
    severity = Severity.WARNING
    category = RuleCategory.SECURITY
    node_type = NodeType.CALL

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Call").where_call(name="eval"),
            match("Call").where_call(name="exec"),
            match("Call").where_call(qual="builtins.eval"),
            match("Call").where_call(qual="builtins.exec"),
        ]
        self.fixer_builders = [
            fix()
            .insert_comment(self._note)
            .because("Dynamic code execution is unsafe and should be avoided."),
        ]

    def _note(self, node):
        func = getattr(node, "func", None)
        name = getattr(func, "name", None) or getattr(func, "id", None)

        if not name:
            try:
                name = func.as_string().rstrip()
            except Exception:
                name = "eval/exec"

        if name.endswith("exec"):
            return (
                "# Insecure use of exec(). Avoid dynamic code execution; "
                "prefer explicit functions, dispatch tables, or controlled plugin loading."
            )

        return (
            "# Insecure use of eval(). If parsing Python literals, use ast.literal_eval(); "
            "otherwise prefer explicit parsing or a dispatch-based design."
        )


class EvalLiteralParsingCandidate(Rule):
    """
    This eval() call appears to be used for parsing Python literals.

    Using eval() for literal parsing is unsafe, as it can execute arbitrary code.
    If the input consists only of Python literals (e.g. strings, numbers, lists,
    dictionaries), ast.literal_eval() provides a safe alternative.

    Consider replacing eval() with ast.literal_eval().
    """
    id = "SEC-035"
    title = "eval() may be replaced with ast.literal_eval()"
    severity = Severity.INFO
    category = RuleCategory.SECURITY
    node_type = NodeType.CALL

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Call").satisfies(self.is_literal_eval_candidate)
        ]
        self.fixer_builders = [
            fix()
            .insert_comment(
                "# If this call only parses Python literals, replace eval() with ast.literal_eval()."
            )
            .because("This eval() call looks like literal parsing."),
            fix()
            .replace_eval_with_literal_eval()
            .because("Replace eval() with ast.literal_eval() for literal parsing."),
        ]

    def is_literal_eval_candidate(self, node) -> bool:
        if node.__class__.__name__ != "Call":
            return False

        func = getattr(node, "func", None)
        name = getattr(func, "name", None) or getattr(func, "id", None)
        if name != "eval":
            return False

        args = getattr(node, "args", None) or []
        keywords = getattr(node, "keywords", None) or []
        if len(args) != 1 or keywords:
            return False

        arg = args[0]
        if arg.__class__.__name__ not in {"Const", "Constant"}:
            return False

        value = getattr(arg, "value", None)
        if not isinstance(value, str):
            return False

        text = value.strip()
        if not text:
            return False

        return text[0] in "([{'\"-0123456789"


class UseOfOsSystem(Rule):
    """
    Use of os.system() or os.popen() detected.

    Shell-based command execution can be unsafe, especially when handling
    untrusted input, as it may lead to command injection vulnerabilities.
    Additionally, these APIs are limited and less flexible.

    Consider using the subprocess module instead, which provides safer and
    more controlled process execution.
    """
    id = "SEC-031"
    title = "Use of os.system()"
    severity = Severity.WARNING
    category = RuleCategory.SECURITY
    node_type = NodeType.CALL

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Call").where_call(qual="os.system"),
            match("Call").where_call(qual="os.popen"),
        ]
        self.fixer_builders = [
            fix()
            .insert_comment(self._note)
            .because("Shell-based process execution is risky."),
            fix()
            .replace_os_system_with_subprocess_run()
            .ensure_import("subprocess")
            .because("Prefer subprocess over os.system()."),
        ]

    def _note(self, node):
        qual = self._qual(node)

        if qual == "os.popen":
            return (
                "# os.popen() is risky and outdated. Prefer subprocess.run(), "
                "subprocess.Popen(), or explicit pipe handling."
            )

        return (
            "# os.system() is risky. Prefer subprocess.run(..., shell=True, check=True) "
            "or a safer argument list without shell=True."
        )

    def _qual(self, node):
        func = getattr(node, "func", None)
        if func is None:
            return None

        if func.__class__.__name__ != "Attribute":
            return None

        base = getattr(func, "expr", None) or getattr(func, "value", None)
        base_name = getattr(base, "name", None) or getattr(base, "id", None)
        attr = getattr(func, "attrname", None) or getattr(func, "attr", None)

        if base_name and attr:
            return f"{base_name}.{attr}"

        return None


class HardcodedPasswordOrKey(Rule):
    """
    Possible hardcoded secret detected.

    Storing passwords, API keys, or tokens directly in source code is insecure,
    as it may expose sensitive data in version control or logs. This increases
    the risk of unauthorized access.

    Consider moving secrets to environment variables or a secure configuration system.
    """
    id = "SEC-033"
    title = "Hardcoded password / key / token"
    severity = Severity.WARNING
    category = RuleCategory.SECURITY
    node_type = {NodeType.ASSIGN, NodeType.ANN_ASSIGN}

    SUSPECT_NAMES = (
        "password", "passwd", "pwd",
        "secret", "token", "apikey", "api_key", "apiKey",
        "access_token", "auth", "credential", "credentials",
        "key",
    )

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Assign|AnnAssign")
            .where_target_contains_any(*self.SUSPECT_NAMES)
            .where_value_is_string_literal(non_empty=True)
        ]
        self.fixer_builders = [
            fix()
            .insert_comment(
                "# Possible hardcoded secret. Move it to environment variables or secure configuration."
            )
            .because("Possible hardcoded secret detected."),
        ]


class InsecureRandom(Rule):
    """
    Insecure use of the random module.

    The random module is not designed for security-sensitive purposes and may
    produce predictable values. Using it for tokens, passwords, or security-related
    operations can lead to vulnerabilities.

    Consider using the secrets module or os.urandom() for secure random values.
    """
    id = "SEC-034"
    title = "Insecure use of random module"
    severity = Severity.WARNING
    category = RuleCategory.SECURITY
    node_type = NodeType.CALL

    UNSAFE_FUNCS = {
        "random", "randint", "randrange", "choice",
        "shuffle", "getrandbits", "uniform", "triangular",
    }

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Call").where_call(qual=f"random.{fn}")
            for fn in self.UNSAFE_FUNCS
        ]
        self.fixer_builders = [
            fix()
            .insert_comment(
                "# Insecure randomness. For security-sensitive code use secrets or os.urandom()."
            )
            .because("The random module is not suitable for security-sensitive values."),
        ]


class OpenWithoutWith(Rule):
    """
    open() is used without a context manager.

    Opening files without a context manager may lead to resource leaks if the file
    is not properly closed, especially in case of errors. Using 'with open(...)'
    ensures that the file is automatically closed.

    Consider using a context manager for safer resource handling.
    """
    id = "RES-032"
    title = "open() used without context manager"
    severity = Severity.WARNING
    category = RuleCategory.RESOURCE
    node_type = NodeType.CALL

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Call").where_call(name="open").missing_parent("With|AsyncWith")
        ]
        self.fixer_builders = [
            fix()
            .insert_comment(
                "# open() used without a context manager. Prefer: with open(...) as f:"
            )
            .because("File handles should usually be managed with a context manager."),
        ]


__all__ = [
    "UseOfEval",
    "EvalLiteralParsingCandidate",
    "UseOfOsSystem",
    "HardcodedPasswordOrKey",
    "InsecureRandom",
    "OpenWithoutWith",
]
