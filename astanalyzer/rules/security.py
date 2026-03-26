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
