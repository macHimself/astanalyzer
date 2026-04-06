"""
Internal helpers for project-wide rename refactors.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..fixer.types import FixProposal


class RenameMixin:
    """Internal mixin with project-wide rename algorithms."""

    def _build_project_wide_rename(
        self,
        *,
        node: Any,
        project,
        project_root,
        get_old_name,
        make_new_name,
        replace_definition,
        replace_imported_usage,
        replace_qualified_usage,
    ) -> list[FixProposal]:
        old_name = get_old_name(node)
        if not isinstance(old_name, str) or not old_name:
            return []

        new_name = make_new_name(old_name)
        if not new_name or new_name == old_name:
            return []

        if project is None:
            return []

        proposals: list[FixProposal] = []

        def_file = str(getattr(node.root(), "file", ""))
        if not def_file:
            return []

        def_module_name = self._module_name_from_path(def_file, project_root)

        for mod in getattr(project, "modules", []):
            file_path = str(mod.filename)
            source = getattr(mod.ast_root, "file_content", None)
            if not isinstance(source, str):
                continue

            changed = source

            if file_path == def_file:
                changed = replace_definition(changed, old_name, new_name)
                changed = replace_imported_usage(changed, old_name, new_name)
            else:
                imported_simple = self._module_imports_name(mod.ast_root, def_module_name, old_name)
                imported_module_aliases = self._module_import_aliases(mod.ast_root, def_module_name)

                if imported_simple:
                    changed = self._replace_import_from_name(changed, old_name, new_name)
                    changed = replace_imported_usage(changed, old_name, new_name)

                if imported_module_aliases:
                    for alias in imported_module_aliases:
                        changed = replace_qualified_usage(changed, alias, old_name, new_name)

            if changed != source:
                proposals.append(
                    FixProposal(
                        original=source,
                        suggestion=changed,
                        reason=self.reason_text(),
                        lineno=1,
                        filename=file_path,
                    )
                )

        return proposals

    def _get_function_old_name(self, node: Any) -> str | None:
        if node.__class__.__name__ != "FunctionDef":
            return None
        return getattr(node, "name", None)

    def _get_class_old_name(self, node: Any) -> str | None:
        if node.__class__.__name__ != "ClassDef":
            return None
        return getattr(node, "name", None)

    def _get_constant_old_name(self, node: Any) -> str | None:
        cname = node.__class__.__name__

        if cname == "Assign":
            targets = getattr(node, "targets", []) or []
            if not targets:
                return None
            target = targets[0]
        elif cname == "AnnAssign":
            target = getattr(node, "target", None)
        else:
            return None

        if target is None:
            return None

        return getattr(target, "name", None) or getattr(target, "id", None)

    def _build_rename_function_project_wide(self, node: Any, module=None, project=None, project_root=None) -> list[FixProposal]:
        return self._build_project_wide_rename(
            node=node,
            project=project,
            project_root=project_root,
            get_old_name=self._get_function_old_name,
            make_new_name=self._to_snake_case,
            replace_definition=self._replace_function_definition_name,
            replace_imported_usage=self._replace_function_imported_usage,
            replace_qualified_usage=self._replace_function_qualified_usage,
        )

    def _build_rename_class_project_wide(self, node: Any, module=None, project=None, project_root=None) -> list[FixProposal]:
        return self._build_project_wide_rename(
            node=node,
            project=project,
            project_root=project_root,
            get_old_name=self._get_class_old_name,
            make_new_name=self._to_pascal_case,
            replace_definition=self._replace_class_definition_name,
            replace_imported_usage=self._replace_class_imported_usage,
            replace_qualified_usage=self._replace_class_qualified_usage,
        )

    def _build_rename_constant_project_wide(self, node: Any, module=None, project=None, project_root=None) -> list[FixProposal]:
        return self._build_project_wide_rename(
            node=node,
            project=project,
            project_root=project_root,
            get_old_name=self._get_constant_old_name,
            make_new_name=self._to_upper_snake_case,
            replace_definition=self._replace_constant_definition_name,
            replace_imported_usage=self._replace_constant_imported_usage,
            replace_qualified_usage=self._replace_constant_qualified_usage,
        )

    def _replace_function_definition_name(self, source: str, old_name: str, new_name: str) -> str:
        pattern = rf"(^\s*def\s+){re.escape(old_name)}(\s*\()"
        return re.sub(pattern, rf"\1{new_name}\2", source, flags=re.MULTILINE)

    def _replace_function_imported_usage(self, source: str, old_name: str, new_name: str) -> str:
        return self._replace_simple_calls(source, old_name, new_name)

    def _replace_function_qualified_usage(self, source: str, module_alias: str, old_name: str, new_name: str) -> str:
        return self._replace_qualified_calls(source, module_alias, old_name, new_name)

    def _replace_class_definition_name(self, source: str, old_name: str, new_name: str) -> str:
        pattern = rf"(^\s*class\s+){re.escape(old_name)}(\b)"
        return re.sub(pattern, rf"\1{new_name}\2", source, flags=re.MULTILINE)

    def _replace_class_imported_usage(self, source: str, old_name: str, new_name: str) -> str:
        source = self._replace_simple_calls(source, old_name, new_name)
        source = self._replace_attribute_base_refs(source, old_name, new_name)
        source = self._replace_base_class_refs(source, old_name, new_name)
        source = self._replace_isinstance_refs(source, old_name, new_name)
        source = self._replace_except_refs(source, old_name, new_name)
        return source

    def _replace_class_qualified_usage(self, source: str, module_alias: str, old_name: str, new_name: str) -> str:
        source = self._replace_qualified_calls(source, module_alias, old_name, new_name)
        source = self._replace_qualified_attribute_base_refs(source, module_alias, old_name, new_name)
        return source

    def _replace_constant_definition_name(self, source: str, old_name: str, new_name: str) -> str:
        pattern = rf"(^\s*){re.escape(old_name)}(\s*:\s*[^=]+=\s*|(\s*=))"
        return re.sub(
            pattern,
            lambda m: f"{m.group(1)}{new_name}{m.group(2)}",
            source,
            flags=re.MULTILINE,
        )

    def _replace_constant_imported_usage(self, source: str, old_name: str, new_name: str) -> str:
        pattern = rf"(?<![\.\w]){re.escape(old_name)}(?![\w])"
        return re.sub(pattern, new_name, source)

    def _replace_constant_qualified_usage(self, source: str, module_alias: str, old_name: str, new_name: str) -> str:
        pattern = rf"(?<!\w){re.escape(module_alias)}\.{re.escape(old_name)}(?![\w])"
        return re.sub(pattern, f"{module_alias}.{new_name}", source)

    def _replace_attribute_base_refs(self, source: str, old_name: str, new_name: str) -> str:
        pattern = rf"(?<![\w\.]){re.escape(old_name)}(?=\s*\.)"
        return re.sub(pattern, new_name, source)

    def _replace_qualified_attribute_base_refs(
        self,
        source: str,
        module_alias: str,
        old_name: str,
        new_name: str,
    ) -> str:
        pattern = rf"(?<!\w){re.escape(module_alias)}\.{re.escape(old_name)}(?=\s*[\.\(])"
        return re.sub(pattern, f"{module_alias}.{new_name}", source)

    def _module_name_from_path(self, file_path: str, project_root) -> str:
        path = Path(file_path).resolve()
        root = Path(project_root).resolve() if project_root else path.parent
        rel = path.relative_to(root)
        parts = list(rel.parts)
        if parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]
        if parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)

    def _module_imports_name(self, ast_root: Any, module_name: str, old_name: str) -> bool:
        for n in ast_root.get_children():
            if n.__class__.__name__ == "ImportFrom":
                modname = getattr(n, "modname", None) or getattr(n, "module", None)
                if modname != module_name:
                    continue
                names = getattr(n, "names", []) or []
                for item in names:
                    if isinstance(item, tuple):
                        imported, alias = item
                    else:
                        imported = getattr(item, "name", None)
                        alias = getattr(item, "asname", None)
                    if imported == old_name and not alias:
                        return True
        return False

    def _module_import_aliases(self, ast_root: Any, module_name: str) -> list[str]:
        aliases: list[str] = []
        for n in ast_root.get_children():
            if n.__class__.__name__ == "Import":
                names = getattr(n, "names", []) or []
                for item in names:
                    if isinstance(item, tuple):
                        imported, alias = item
                    else:
                        imported = getattr(item, "name", None)
                        alias = getattr(item, "asname", None)
                    if imported == module_name:
                        aliases.append(alias or imported.split(".")[-1])
        return aliases

    def _replace_import_from_name(self, source: str, old_name: str, new_name: str) -> str:
        pattern = rf"(\bfrom\s+[A-Za-z0-9_\.]+\s+import\s+[^\n]*\b){re.escape(old_name)}(\b)"
        return re.sub(pattern, rf"\1{new_name}\2", source)

    def _replace_simple_calls(self, source: str, old_name: str, new_name: str) -> str:
        pattern = rf"(?<![\.\w]){re.escape(old_name)}(?=\s*\()"
        return re.sub(pattern, new_name, source)

    def _replace_qualified_calls(self, source: str, module_alias: str, old_name: str, new_name: str) -> str:
        pattern = rf"(?<!\w){re.escape(module_alias)}\.{re.escape(old_name)}(?=\s*\()"
        return re.sub(pattern, f"{module_alias}.{new_name}", source)

    def _replace_base_class_refs(self, source: str, old_name: str, new_name: str) -> str:
        pattern = rf"(\bclass\s+[A-Za-z_][A-Za-z0-9_]*\s*\([^)]*)\b{re.escape(old_name)}\b"
        return re.sub(pattern, lambda m: m.group(0).replace(old_name, new_name), source)

    def _replace_isinstance_refs(self, source: str, old_name: str, new_name: str) -> str:
        pattern = rf"(\bisinstance\s*\([^,]+,\s*){re.escape(old_name)}(\b)"
        return re.sub(pattern, rf"\1{new_name}\2", source)

    def _replace_except_refs(self, source: str, old_name: str, new_name: str) -> str:
        pattern = rf"(\bexcept\s+){re.escape(old_name)}(\b)"
        return re.sub(pattern, rf"\1{new_name}\2", source)
