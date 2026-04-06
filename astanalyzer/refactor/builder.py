"""
Public builder for project-wide refactor proposals.
"""

from __future__ import annotations

from typing import Any

from ..fixer.builder import ProposalBuilder
from ..fixer.types import FixProposal
from ..utils.naming import to_pascal_case, to_snake_case, to_upper_snake_case
from .rename import RenameMixin


class RefactorBuilder(ProposalBuilder, RenameMixin):
    """Builder for project-wide or multi-file refactor proposals."""

    def __init__(self) -> None:
        super().__init__(title="Proposed refactor")
        self.operations: list[dict[str, Any]] = []

        self._to_snake_case = to_snake_case
        self._to_pascal_case = to_pascal_case
        self._to_upper_snake_case = to_upper_snake_case

    def rename_constant_project_wide(self) -> "RefactorBuilder":
        self.operations.append({"op": "rename_constant_project_wide"})
        return self

    def rename_function_project_wide(self) -> "RefactorBuilder":
        self.operations.append({"op": "rename_function_project_wide"})
        return self

    def rename_class_project_wide(self) -> "RefactorBuilder":
        self.operations.append({"op": "rename_class_project_wide"})
        return self

    def _actions_for_dict(self) -> list[dict[str, Any]]:
        return self.operations

    def build(self, node: Any, module=None, project=None, project_root=None, refs=None) -> list[FixProposal]:
        ops = [op.get("op") for op in self.operations]

        if "rename_function_project_wide" in ops:
            return self._build_rename_function_project_wide(
                node=node,
                module=module,
                project=project,
                project_root=project_root,
            )

        if "rename_class_project_wide" in ops:
            return self._build_rename_class_project_wide(
                node=node,
                module=module,
                project=project,
                project_root=project_root,
            )

        if "rename_constant_project_wide" in ops:
            return self._build_rename_constant_project_wide(
                node=node,
                module=module,
                project=project,
                project_root=project_root,
            )

        return []


def refactor_builder() -> RefactorBuilder:
    """Create a new RefactorBuilder."""
    return RefactorBuilder()
