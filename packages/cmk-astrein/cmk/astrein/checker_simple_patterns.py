#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import ast
from pathlib import Path, PurePosixPath

from cmk.astrein.framework import ASTVisitorChecker


class ABCMetaMetaclassChecker(ASTVisitorChecker):
    """Detects use of `metaclass=ABCMeta` instead of inheriting from ABC."""

    def checker_id(self) -> str:
        return "abcmeta-metaclass"

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for keyword in node.keywords:
            if keyword.arg == "metaclass" and self._is_abcmeta(keyword.value):
                self.add_error(
                    "Use `class Foo(ABC):` instead of `metaclass=ABCMeta`",
                    node,
                )
        self.generic_visit(node)

    @staticmethod
    def _is_abcmeta(node: ast.expr) -> bool:
        if isinstance(node, ast.Name) and node.id == "ABCMeta":
            return True
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "ABCMeta"
            and isinstance(node.value, ast.Name)
            and node.value.id == "abc"
        ):
            return True
        return False


class HTMLDebugChecker(ASTVisitorChecker):
    """Detects calls to `html.debug(...)`."""

    def checker_id(self) -> str:
        return "html-debug"

    def visit_Call(self, node: ast.Call) -> None:
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "debug"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "html"
        ):
            self.add_error("Found html.debug call", node)
        self.generic_visit(node)


class PillowImportChecker(ASTVisitorChecker):
    """Detects direct imports of PIL.

    PIL should be wrapped in a dedicated images module at the correct layer
    (e.g. cmk.gui.utils.images for GUI code).
    """

    def checker_id(self) -> str:
        return "pillow-import"

    def visit_Import(self, node: ast.Import) -> None:
        if self._is_excluded():
            return
        for alias in node.names:
            if alias.name == "PIL" or alias.name.startswith("PIL."):
                self.add_error(
                    "PIL should not be used directly. Wrap it in a dedicated images "
                    "module at the correct layer (e.g. cmk.gui.utils.images for GUI code).",
                    node,
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if self._is_excluded():
            return
        if node.module is not None and (node.module == "PIL" or node.module.startswith("PIL.")):
            self.add_error(
                "PIL should not be used directly. Wrap it in a dedicated images "
                "module at the correct layer (e.g. cmk.gui.utils.images for GUI code).",
                node,
            )
        self.generic_visit(node)

    def _is_excluded(self) -> bool:
        return PurePosixPath(self.file_path) == PurePosixPath(
            self.repo_root / "cmk" / "gui" / "utils" / "images.py"
        )


class PydanticTypeAdapterChecker(ASTVisitorChecker):
    """Detects TypeAdapter() calls inside function/method bodies (module-level is fine)."""

    def checker_id(self) -> str:
        return "pydantic-type-adapter"

    def __init__(self, file_path: Path, repo_root: Path, source_code: str) -> None:
        super().__init__(file_path, repo_root, source_code)
        self._function_depth = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function_depth += 1
        self.generic_visit(node)
        self._function_depth -= 1

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function_depth += 1
        self.generic_visit(node)
        self._function_depth -= 1

    def visit_Call(self, node: ast.Call) -> None:
        if self._function_depth > 0 and self._is_type_adapter_call(node):
            self.add_error(
                "TypeAdapter() is costly. Ensure it doesn't impact performance."
                " If acceptable, suppress with `# astrein: disable=pydantic-type-adapter`",
                node,
            )
        self.generic_visit(node)

    @staticmethod
    def _is_type_adapter_call(node: ast.Call) -> bool:
        func = node.func
        if isinstance(func, ast.Name) and func.id == "TypeAdapter":
            return True
        if (
            isinstance(func, ast.Subscript)
            and isinstance(func.value, ast.Name)
            and func.value.id == "TypeAdapter"
        ):
            return True
        return False


class TarfileOpenReadChecker(ASTVisitorChecker):
    """Detects tarfile.open() / TarFile.open() in read mode."""

    def checker_id(self) -> str:
        return "tarfile-open-read"

    _EXCLUDED_DIRS = frozenset({"mkp_tool", "tests", "testlib"})

    def visit_Call(self, node: ast.Call) -> None:
        if self._is_excluded():
            self.generic_visit(node)
            return
        if self._is_tarfile_open(node) and self._is_read_mode(node):
            self.add_error(
                "tarfile.open() in read mode should not be used directly."
                " Use CheckmkTarArchive.from_(bytes|buffer|path) method instead",
                node,
            )
        self.generic_visit(node)

    def _is_excluded(self) -> bool:
        parts = PurePosixPath(self.file_path.relative_to(self.repo_root)).parts
        return bool(self._EXCLUDED_DIRS & set(parts))

    @staticmethod
    def _is_tarfile_open(node: ast.Call) -> bool:
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "open":
            return False
        value = node.func.value
        if isinstance(value, ast.Name):
            name = value.id
            return name in ("tarfile", "TarFile") or name.endswith("tf")
        return False

    @staticmethod
    def _is_read_mode(node: ast.Call) -> bool:
        for kw in node.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                return isinstance(kw.value.value, str) and kw.value.value.startswith("r")
        # Check positional: tarfile.open(name, mode) — mode is the 2nd positional arg
        if len(node.args) >= 2:
            mode_arg = node.args[1]
            if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str):
                return mode_arg.value.startswith("r")
        # No mode specified at all — defaults to "r"
        if not any(kw.arg == "mode" for kw in node.keywords) and len(node.args) < 2:
            return True
        return False
