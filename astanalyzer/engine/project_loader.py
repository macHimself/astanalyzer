from __future__ import annotations

import logging
import os

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from astroid import nodes, parse
from astroid.exceptions import AstroidSyntaxError
from colorama import init

log = logging.getLogger(__name__)
init(autoreset=True)


def _syntax_loc(err):
    """
    Extract line/column from SyntaxError or AstroidSyntaxError.

    Astroid may hide the original syntax error inside ``__cause__``.
    """
    base = getattr(err, "__cause__", None) or err
    lineno = getattr(base, "lineno", None)
    col = getattr(base, "offset", None)
    return lineno, col


def get_list_of_files_in_project(location: str) -> List[str]:
    """
    Collect Python files from a single file path or recursively from a directory.
    """
    skip_dirs = {".git", ".venv", "venv", "UPOL", "dist", "build", "__pycache__"}
    file_list: List[str] = []

    if os.path.isfile(location) and location.endswith(".py"):
        file_list.append(location)
    elif os.path.isdir(location):
        for root, dirs, files in os.walk(location):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith("_")]
            for file in files:
                if file.endswith(".py") and not file.startswith("_"):
                    file_list.append(os.path.join(root, file))
    else:
        raise FileNotFoundError(
            f"Input path '{location}' is not a valid Python file or directory."
        )

    return file_list


def git_root(start: Path | None = None) -> Path:
    """
    Find git root by walking up to the first directory containing ``.git``.
    """
    p = (start or Path.cwd()).resolve()

    for parent in [p, *p.parents]:
        if (parent / ".git").exists():
            return parent

    return Path.cwd()


class ModuleNode:
    """
    Parsed Python module wrapper.
    """

    def __init__(self, filename: str, ast_root: nodes.Module):
        self.filename = filename
        self.ast_root = ast_root


@dataclass(frozen=True)
class ParseError:
    file: str
    message: str
    lineno: Optional[int] = None
    col_offset: Optional[int] = None
    error_type: str = "PARSE_ERROR"


class ProjectNode:
    """
    Container for parsed project modules and AST traversal helpers.
    """

    def __init__(self):
        self.modules: List[ModuleNode] = []
        self.root_dir: Path | None = None
        self.parse_errors: List[ParseError] = []

    def add_module(self, module: ModuleNode) -> None:
        self.modules.append(module)

    def add_parse_error(self, filepath: str, message: str, lineno=None, col_offset=None):
        self.parse_errors.append(
            ParseError(
                file=filepath,
                message=message,
                lineno=lineno,
                col_offset=col_offset,
            )
        )

    def walk_astroid_tree(self, node: nodes.NodeNG):
        yield node
        try:
            children = node.get_children()
        except Exception:
            return
        for child in children:
            yield from self.walk_astroid_tree(child)

    def walk_all_nodes(self):
        for module in self.modules:
            root = module.ast_root
            for node in self.walk_astroid_tree(root):
                yield module, node

    def walk_all_nodes_visual(self):
        for module in self.modules:
            root = module.ast_root
            for node in self.walk_astroid_tree(root):
                node_type = node.__class__.__name__
                lineno = getattr(node, "lineno", "?")
                name = (
                    getattr(node, "name", None)
                    or getattr(node, "attrname", None)
                    or getattr(node, "id", None)
                    or ""
                )
                log.debug("%s:%s -> %s %s", module.filename, lineno, node_type, name)
                yield node_type


def resolve_project_root(project_files: List[str]) -> Path | None:
    if not project_files:
        return None

    common = Path(os.path.commonpath(project_files)).resolve()

    if common.is_file() or common.suffix == ".py":
        return git_root(common.parent)

    return common


def read_source_file(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def parse_source(filepath: str, code: str) -> nodes.Module:
    return parse(code, module_name=str(filepath))


def attach_tree_metadata(tree: nodes.Module, filepath: str, code: str) -> None:
    tree.file = filepath
    tree.file_content = code
    tree.file_by_lines = code.splitlines(keepends=True)


def handle_parse_exception(
    project: ProjectNode,
    filepath: str,
    code: str,
    exc: Exception,
) -> None:
    base = getattr(exc, "__cause__", None) or exc
    lineno, col = _syntax_loc(exc)

    snippet = ""
    if lineno is not None:
        lines = code.splitlines()
        if 1 <= lineno <= len(lines):
            bad_line = lines[lineno - 1]
            caret = " " * max((col or 1) - 1, 0) + "^"
            snippet = f"\n    {bad_line}\n    {caret}"

    log.warning(
        "Syntax error in %s:%s:%s: %s%s",
        filepath,
        lineno,
        col,
        base,
        snippet,
    )

    project.add_parse_error(
        filepath=filepath,
        message=str(base),
        lineno=lineno,
        col_offset=col,
    )


def load_single_module(filepath: str) -> ModuleNode:
    code = read_source_file(filepath)
    tree = parse_source(filepath, code)
    attach_tree_metadata(tree, filepath, code)
    return ModuleNode(filename=filepath, ast_root=tree)


def load_project(project_files: List[str]) -> ProjectNode:
    project = ProjectNode()
    project.root_dir = resolve_project_root(project_files)

    for filepath in project_files:
        try:
            code = read_source_file(filepath)
        except OSError as e:
            project.add_parse_error(filepath, str(e))
            continue

        try:
            tree = parse_source(filepath, code)
        except (SyntaxError, IndentationError, AstroidSyntaxError) as e:
            handle_parse_exception(project, filepath, code, e)
            continue

        attach_tree_metadata(tree, filepath, code)
        project.add_module(ModuleNode(filename=filepath, ast_root=tree))

    return project


def count_lines(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0
