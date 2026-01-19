#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Checker to prevent disallowed imports of modules."""

from __future__ import annotations

import ast
from pathlib import Path

from cmk.astrein.framework import ASTVisitorChecker
from cmk.astrein.module_layers_config import (
    _EXPLICIT_FILE_TO_COMPONENT,
    _EXPLICIT_FILE_TO_DEPENDENCIES,
    Component,
    COMPONENTS,
    get_absolute_importee,
    ModuleName,
    ModulePath,
)


class ModuleLayersChecker(ASTVisitorChecker):
    """Checker for module layer architecture violations.

    Enforces architectural boundaries between different components of the
    Checkmk codebase based on the COMPONENTS mapping.
    """

    def __init__(self, file_path: Path, repo_root: Path, source_code: str):
        super().__init__(file_path, repo_root, source_code)

        # Compute module name from file path
        self.module_name = self._compute_module_name()

        # Check if this is a package
        self.is_package = file_path.name == "__init__.py"

        # Compute relative path from repo root
        try:
            self.relative_path = ModulePath(file_path.relative_to(repo_root))
        except ValueError:
            # File is outside repo (e.g., /tmp files)
            self.relative_path = ModulePath(file_path)

        # Find the component this file belongs to
        self.component = self._find_component(self.module_name, self.relative_path)

    def checker_id(self) -> str:
        return "cmk-module-layer-violation"

    def _compute_module_name(self) -> ModuleName:
        """Compute module name from file path"""
        # Due to our symlinks and pasting magic, we need to compute the
        # real module name from the file path of the module.
        # Emacs' flycheck stores files to be checked in a temporary file with a prefix.
        p = ModulePath(
            self.file_path.with_name(
                self.file_path.name.removeprefix("flycheck_").removesuffix(".py")
            )
        )

        # Try to make it relative to repo_root
        try:
            p = ModulePath(p.relative_to(self.repo_root))
        except ValueError:
            # File is outside repo, use as-is
            pass

        if p.is_below("cmk") or p.is_below("tests"):
            return ModuleName(".".join(p.parts))

        if p.is_below("omd/packages/omd/omdlib"):
            return ModuleName(".".join(p.parts[3:]))

        if p.is_below("packages"):
            return ModuleName(".".join(p.parts[2:]))

        if p.is_below("non-free/packages"):
            return ModuleName(".".join(p.parts[3:]))

        # For all modules which don't live below cmk after mangling, just assume a toplevel module.
        return ModuleName(p.parts[-1] if p.parts else self.file_path.stem)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._check_import(node, ModuleName(alias.name))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level in {1, 2}:
            # This is a relative import. Assume this is fine.
            self.generic_visit(node)
            return

        # IMPORTANT: In ast module, the attribute is 'module', not 'modname'!
        if node.module is None:
            self.generic_visit(node)
            return

        imported = [f"{node.module}.{alias.name}" for alias in node.names]
        for modname in imported:
            self._check_import(
                node,
                (
                    ModuleName(modname)
                    if node.level == 0
                    else get_absolute_importee(
                        root_name=str(self.module_name),
                        modname=modname,
                        level=node.level,
                        is_package=self.is_package,
                    )
                ),
            )
        self.generic_visit(node)

    def _check_import(self, node: ast.Import | ast.ImportFrom, imported: ModuleName) -> None:
        """Check if an import is allowed"""
        if self._shall_exclude_file_below_packages(self.relative_path):
            return

        # We only care about imports of our own modules.
        # ... blissfully ignoring tests/.
        if not imported.in_component(Component("cmk")):
            return

        if not self._is_import_allowed(self.component, self.relative_path, imported):
            self.add_error(
                f"Import of {imported} not allowed in {self.component or self.module_name!r}",
                node,
            )

    @staticmethod
    def _shall_exclude_file_below_packages(relative_path: ModulePath) -> bool:
        """Exclude files in "tests" or other non cmk related directories below packages

        This is not just a lazy shortcut. The layer checker is supposed to ensure
        rules in the cmk namespace. Dependencies of the package's tests are managed through
        bazel dependencies. We feel no need to enforce cmk module layer rules there.
        """
        base_paths = ["packages", "non-free/packages"]
        for base_path in base_paths:
            if relative_path.is_below(base_path):
                relative_to_pkg = ModulePath(*relative_path.relative_to(base_path).parts[1:])
                if not relative_to_pkg.is_below("cmk"):
                    return True
        return False

    def _is_import_allowed(
        self, component: Component | None, importing_path: ModulePath, imported: ModuleName
    ) -> bool:
        """Check if an import is allowed based on component rules"""
        if component:
            return COMPONENTS[component](imported=imported, component=component)

        try:
            file_specific_checker = _EXPLICIT_FILE_TO_DEPENDENCIES[importing_path]
        except KeyError:
            # This file does not belong to any component, and is not listed in
            # _EXPLICIT_FILE_TO_DEPENDENCIES. We don't allow any cmk imports.
            return False
        return file_specific_checker(imported=imported, component=component)

    @staticmethod
    def _find_component(importing: ModuleName, importing_path: ModulePath) -> Component | None:
        """Find which component a file belongs to"""
        # Let's *not* check the explicit list first. We don't want to encourage to define exceptions.
        # What's below cmk/foobar, belongs to cmk.foobar, PERIOD.
        for component in COMPONENTS:
            if importing.in_component(component):
                return component
        try:
            return _EXPLICIT_FILE_TO_COMPONENT[importing_path]
        except KeyError:
            return None
