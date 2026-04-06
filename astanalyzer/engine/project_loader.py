"""
Project loading and AST preparation utilities.

This module is responsible for discovering Python source files, parsing them
into astroid module trees, attaching source-related metadata, and collecting
parse errors encountered during loading.

It also defines lightweight project and module containers used by the analysis
engine to iterate over parsed modules and traverse their AST nodes.
"""
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


def _syntax_loc(err):
    """
    Extract line and column information from a parsing exception.

    Astroid may wrap the original syntax-related exception inside `__cause__`,
    so this helper attempts to read location data from the innermost error.
    """
    base = getattr(err, "__cause__", None) or err
    lineno = getattr(base, "lineno", None)
    col = getattr(base, "offset", None)
    return lineno, col


def get_list_of_files_in_project(location: str) -> List[str]:
    """
    Collect Python source files from a file path or recursively from a directory.

    Hidden and ignored directories such as `.git`, virtual environments,
    build outputs, and cache directories are skipped.
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
    Resolve the nearest Git repository root by walking upwards from the start path.

    If no `.git` directory is found, the current working directory is returned.
    """
    p = (start or Path.cwd()).resolve()

    for parent in [p, *p.parents]:
        if (parent / ".git").exists():
            return parent

    return Path.cwd()


class ModuleNode:
    """
    Lightweight wrapper around a parsed Python module.

    Stores the original filename together with the parsed astroid module root.
    """

    def __init__(self, filename: str, ast_root: nodes.Module):
        self.filename = filename
        self.ast_root = ast_root


@dataclass(frozen=True)
class ParseError:
    """
    Structured record describing a source file parsing failure.

    Stores the affected file, human-readable error message, and optional
    source location metadata.
    """
    file: str
    message: str
    lineno: Optional[int] = None
    col_offset: Optional[int] = None
    error_type: str = "PARSE_ERROR"


class ProjectNode:
    """
    Container for parsed project modules and parse errors.

    Provides helper methods for storing successfully parsed modules,
    recording parse failures, and traversing all nodes across the project.
    """

    def __init__(self):
        self.modules: List[ModuleNode] = []
        self.root_dir: Path | None = None
        self.parse_errors: List[ParseError] = []

    def add_module(self, module: ModuleNode) -> None:
        """Add a parsed module to the project."""
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
        """
        Yield a depth-first traversal of an astroid subtree.

        Traversal stops silently if child access fails for a node.
        """
        yield node
        try:
            children = node.get_children()
        except Exception:
            return
        for child in children:
            yield from self.walk_astroid_tree(child)

    def walk_all_nodes(self):
        """
        Yield `(module, node)` pairs for all parsed nodes in the project.
        """
        for module in self.modules:
            root = module.ast_root
            for node in self.walk_astroid_tree(root):
                yield module, node

    def walk_all_nodes_visual(self):
        """
        Log and yield visual summaries of all parsed nodes for debugging purposes.
        """
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
    """
    Infer the logical project root from the loaded file set.

    For a single file or a file-based common path, the nearest Git root is used.
    Otherwise, the common filesystem path of all project files is returned.
    """
    if not project_files:
        return None

    common = Path(os.path.commonpath(project_files)).resolve()

    if common.is_file() or common.suffix == ".py":
        return git_root(common.parent)

    return common


def read_source_file(filepath: str) -> str:
    """Read and return UTF-8 source code from a file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def parse_source(filepath: str, code: str) -> nodes.Module:
    """Parse source code into an astroid module tree."""
    return parse(code, module_name=str(filepath))


def attach_tree_metadata(tree: nodes.Module, filepath: str, code: str) -> None:
    """
    Attach source-related metadata to a parsed astroid module tree.

    Metadata includes the original file path, full source text, and
    line-preserving source split used by later analysis and patch generation.
    """
    tree.file = filepath
    tree.file_content = code
    tree.file_by_lines = code.splitlines(keepends=True)


def handle_parse_exception(
    project: ProjectNode,
    filepath: str,
    code: str,
    exc: Exception,
) -> None:
    """
    Convert a parsing exception into a structured project parse error.

    Logs a warning with optional source snippet and stores the error
    on the project object.
    """
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
    """
    Load, parse, and wrap a single Python source file as a ModuleNode.
    """
    code = read_source_file(filepath)
    tree = parse_source(filepath, code)
    attach_tree_metadata(tree, filepath, code)
    return ModuleNode(filename=filepath, ast_root=tree)


def load_project(project_files: List[str]) -> ProjectNode:
    """
    Load a project from a list of Python source files.

    Each file is read, parsed into an astroid module tree, enriched with
    source metadata, and stored in the returned project container.
    Files that cannot be read or parsed are recorded as parse errors
    instead of aborting the whole load process.
    """
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
    """
    Count lines in a text file.

    Returns 0 if the file cannot be read.
    """
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0
