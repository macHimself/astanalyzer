"""
Dynamic loading of user-defined rule modules.

This module provides utilities for importing external Python files
containing custom analysis rules into the astanalyzer runtime.

Rules are imported dynamically using importlib to ensure that:
- each file is loaded as a unique module
- name collisions are avoided
- modules can be loaded from arbitrary filesystem locations

Supported inputs:
- a single .py file
- a directory (recursively scanned for .py files)

Imported modules are executed on load, allowing them to register rules
via side effects (e.g. class registration, decorators, metaclasses).

Notes:
- Files starting with '_' are ignored when scanning directories.
- Each imported file is assigned a unique module name based on its path.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _import_python_file(file_path: Path) -> None:
    """
    Import a Python file as a uniquely named module.

    The module name is generated from the file name and its absolute path
    to avoid collisions when importing multiple user rule files.

    Side Effects:
        - Executes the module code
        - Registers it in sys.modules
    """
    module_name = f"astanalyzer_user_rules_{file_path.stem}_{abs(hash(file_path.resolve()))}"

    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create import spec for: {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)


def import_rules_from_path(path: str | Path) -> list[Path]:
    """
    Import user-defined rule modules from a Python file or from all .py files
    inside a directory tree.

    Returns a list of imported Python files.
    """
    target = Path(path).expanduser().resolve()

    if not target.exists():
        raise FileNotFoundError(f"Rules path does not exist: {target}")

    imported: list[Path] = []

    if target.is_file():
        if target.suffix != ".py":
            raise ValueError(f"Rules file must be a .py file: {target}")
        _import_python_file(target)
        imported.append(target)
        return imported

    if target.is_dir():
        for file_path in sorted(target.rglob("*.py")):
            if file_path.name.startswith("_"):
                continue
            _import_python_file(file_path)
            imported.append(file_path)
        return imported

    raise ValueError(f"Unsupported rules path: {target}")