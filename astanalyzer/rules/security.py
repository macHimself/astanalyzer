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

from ..tools import (
    is_builtin_eval_or_exec_call, 
    is_explicit_builtins_eval_or_exec_call, 
    is_builtin_eval_literal_candidate, 
    is_builtin_os_system_or_popen_call, 
    is_hardcoded_secret_assignment, 
    is_insecure_random_call, 
    is_builtin_open_call
)

class UseOfEval(Rule):
    """
    WHAT:
    Detects calls to eval() or exec(), including explicit access through builtins.

    WHY:
    eval() and exec() execute dynamic Python code. If any part of the executed
    string can be influenced by external or untrusted input, the program may allow
    arbitrary code execution. Even with trusted input, dynamic execution makes the
    code harder to reason about, test, and secure.

    WHEN:
    This is critical when input comes from users, files, network data, databases,
    configuration, or any external source. It may be acceptable only in highly
    controlled internal tooling, sandboxes, educational examples, or plugin systems
    with strict isolation and clear trust boundaries.

    HOW:
    Avoid dynamic code execution. Use explicit parsing, dispatch tables, normal
    function calls, or controlled plugin loading instead. If eval() is only used
    to parse Python literals, replace it with ast.literal_eval().
    """
    id = "SEC-001"
    title = "Use of eval()/exec()"
    severity = Severity.WARNING
    category = RuleCategory.SECURITY
    node_type = NodeType.CALL

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Call").satisfies(is_builtin_eval_or_exec_call),
            match("Call").satisfies(is_explicit_builtins_eval_or_exec_call),            
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
    WHAT:
    Detects eval() calls that appear to be used for parsing Python literal values.

    WHY:
    Using eval() for parsing is unsafe because it can execute arbitrary Python code,
    not only read data. This creates an unnecessary security risk when the expected
    input is limited to simple literals such as strings, numbers, lists, tuples, or
    dictionaries.

    WHEN:
    This is relevant when eval() receives data that represents a Python literal,
    especially data loaded from files, user input, logs, configuration, or network
    sources. It should not be blindly replaced if the expression intentionally
    contains executable Python code, although such design should be reviewed.

    HOW:
    Replace eval() with ast.literal_eval() when the input is expected to contain
    only Python literals. If the input format is not Python-specific, prefer a
    dedicated parser such as json.loads() for JSON data.
    """
    id = "SEC-002"
    title = "eval() may be replaced with ast.literal_eval()"
    severity = Severity.INFO
    category = RuleCategory.SECURITY
    node_type = NodeType.CALL

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Call").satisfies(is_builtin_eval_literal_candidate)
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


class UseOfOsSystem(Rule):
    """
    WHAT:
    Detects shell command execution through os.system() or os.popen().

    WHY:
    Shell-based execution is risky because command strings can be vulnerable to
    command injection when they include external input. These APIs also provide
    limited control over arguments, errors, output handling, and return values
    compared with the subprocess module.

    WHEN:
    This is especially dangerous when command strings contain user input, file
    names, environment values, or data from external systems. It may be acceptable
    for small trusted scripts, but production code should still prefer explicit
    process execution through subprocess.

    HOW:
    Use subprocess.run() or subprocess.Popen() instead. Prefer passing arguments
    as a list with shell=False. If shell=True is required, validate and quote all
    inputs carefully and handle errors explicitly, for example with check=True.
    """
    id = "SEC-003"
    title = "Use of os.system()"
    severity = Severity.WARNING
    category = RuleCategory.SECURITY
    node_type = NodeType.CALL

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Call").satisfies(is_builtin_os_system_or_popen_call),
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
    WHAT:
    Detects assignments that appear to store passwords, tokens, API keys, or other
    secrets directly in source code.

    WHY:
    Secrets committed to source code can be exposed through version control,
    logs, backups, package distributions, or shared repositories. Once exposed,
    they may allow unauthorised access and usually must be rotated.

    WHEN:
    This is critical for real credentials, production tokens, private keys, and
    access secrets. It may be a false positive for placeholder values, tests,
    documentation examples, or non-secret variables with names such as "key" that
    do not contain sensitive data.

    HOW:
    Move secrets out of source code. Use environment variables, secret managers,
    deployment configuration, or encrypted configuration storage. If the value is
    only a placeholder or test fixture, make that explicit and suppress the finding
    where appropriate.
    """
    id = "SEC-004"
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
            match("Assign|AnnAssign").satisfies(
                lambda node: is_hardcoded_secret_assignment(node, self.SUSPECT_NAMES)
            )
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
    WHAT:
    Detects use of functions from the random module in contexts that may require
    unpredictable random values.

    WHY:
    The random module is designed for simulations and general-purpose randomness,
    not security. Its output can be predictable and should not be used for tokens,
    passwords, session identifiers, cryptographic keys, or other security-sensitive
    values.

    WHEN:
    This is important whenever random values protect access, identity, secrets, or
    security decisions. It is usually acceptable for games, simulations, sampling,
    tests, visual effects, or non-security-related randomisation.

    HOW:
    Use the secrets module for tokens, passwords, and security-sensitive choices.
    Use os.urandom() or cryptographic libraries when raw secure random bytes are
    required. Keep random only for non-security use cases.
    """
    id = "SEC-005"
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
            match("Call").satisfies(lambda node: is_insecure_random_call(node, self.UNSAFE_FUNCS))
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
    WHAT:
    Detects calls to open() that are not used inside a with or async with context
    manager.

    WHY:
    Files opened without a context manager may not be closed correctly if an
    exception occurs or if the function exits early. This can cause resource leaks,
    locked files, incomplete writes, or inconsistent behaviour in long-running
    programs.

    WHEN:
    This is most relevant in production code, repeated file processing, services,
    and code that opens many files. It may be acceptable when the file object is
    returned to the caller, managed by another owner, or deliberately kept open
    for a longer lifetime.

    HOW:
    Use a context manager, for example with open(...) as f:, so the file is closed
    automatically. If ownership is intentionally transferred or managed elsewhere,
    document that decision or suppress the finding.
    """
    id = "SEC-006"
    title = "open() used without context manager"
    severity = Severity.WARNING
    category = RuleCategory.SECURITY
    node_type = NodeType.CALL

    def __init__(self):
        super().__init__()
        self.matchers = [
            match("Call").satisfies(is_builtin_open_call).missing_parent("With|AsyncWith")
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
