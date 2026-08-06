#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import ast
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import override

from cmk.astrein.framework import ASTVisitorChecker
from cmk.astrein.placeholders import has_positional_placeholder


class ABCMetaMetaclassChecker(ASTVisitorChecker):
    """Detects use of `metaclass=ABCMeta` instead of inheriting from ABC."""

    @override
    def checker_id(self) -> str:
        return "abcmeta-metaclass"

    @override
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
        return (isinstance(node, ast.Name) and node.id == "ABCMeta") or (
            isinstance(node, ast.Attribute)
            and node.attr == "ABCMeta"
            and isinstance(node.value, ast.Name)
            and node.value.id == "abc"
        )


class HTMLDebugChecker(ASTVisitorChecker):
    """Detects calls to `html.debug(...)`."""

    @override
    def checker_id(self) -> str:
        return "html-debug"

    @override
    def visit_Call(self, node: ast.Call) -> None:
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "debug"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "html"
        ):
            self.add_error("Found html.debug call", node)
        self.generic_visit(node)


_LOGGING_METHODS = frozenset({"log", "debug", "info", "warning", "error", "exception", "critical"})

#: Repo-relative path prefixes not yet migrated; the checker skips files below them.
#: Transitional: shrink until empty, then remove this exclusion.
_EXCLUDED_PREFIXES = (
    "cmk",
    "tests",
)

#: Repo-relative paths force-checked even when they sit below an ``_EXCLUDED_PREFIXES``
#: entry, so individual files can be migrated ahead of their surrounding tree.
_INCLUDED_PATHS = (
    "cmk/piggyback",
    "cmk/plugins",
    "cmk/update_config",
    "cmk/base",
    "cmk/utils",
    "cmk/special_agents",
    "cmk/automations",
    "cmk/bi",
    "cmk/config_anonymizer",
    "cmk/gui",
    "cmk/post_rename_site",
    "cmk/product_usage",
)


class LoggingNamedPlaceholderChecker(ASTVisitorChecker):
    """Requires logging calls to use named ``%(name)s`` placeholders.

    Positional ``logger.info("%s unknown to %s", a, b)`` is forbidden in favour of
    ``logger.info("%(thing)s unknown to %(target)s", {"thing": a, "target": b})``.

    ruff's ``G``/``LOG`` rules already ensure logging uses lazy ``%``-style formatting with
    a literal template (rejecting f-strings, ``str.format`` and string concatenation), but
    they do not distinguish positional from named placeholders. This checker adds that
    distinction; because ruff guarantees the literal template, only ``ast.Constant`` string
    messages need to be inspected here.
    """

    def __init__(
        self,
        file_path: Path,
        repo_root: Path,
        source_code: str,
        *,
        excluded_prefixes: Sequence[str] = _EXCLUDED_PREFIXES,
        included_paths: Sequence[str] = _INCLUDED_PATHS,
    ) -> None:
        super().__init__(file_path, repo_root, source_code)
        self._excluded_prefixes = excluded_prefixes
        self._included_paths = included_paths

    @override
    def checker_id(self) -> str:
        return "logging-named-placeholder"

    @override
    def visit_Call(self, node: ast.Call) -> None:
        if not self._is_excluded():
            self._check(node)
        self.generic_visit(node)

    def _is_excluded(self) -> bool:
        try:
            relative_path = PurePosixPath(self.file_path.relative_to(self.repo_root))
        except ValueError:
            return False
        if any(relative_path.is_relative_to(path) for path in self._included_paths):
            return False
        return any(relative_path.is_relative_to(prefix) for prefix in self._excluded_prefixes)

    def _check(self, node: ast.Call) -> None:
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr not in _LOGGING_METHODS:
            return

        # `.log(level, msg, *args)` shifts the message one slot to the right.
        message_index = 1 if func.attr == "log" else 0
        # No format args -> "%s" is literal text, not a placeholder.
        if len(node.args) <= message_index + 1:
            return

        message = node.args[message_index]
        if not isinstance(message, ast.Constant) or not isinstance(message.value, str):
            return

        if has_positional_placeholder(message.value):
            self.add_error(
                "Logging calls must use named `%(name)s` placeholders with a mapping argument, "
                "so each value is labelled in the template. Positional placeholders render as "
                'e.g. "denied 10.0.2.15 to 93.184.216.34 via 10.0.2.1", leaving it unclear which '
                'value is which. Use logger.info("denied %(client_ip)s to %(dest_ip)s via '
                '%(gateway_ip)s", {"client_ip": ..., "dest_ip": ..., "gateway_ip": ...}) instead '
                'of logger.info("denied %s to %s via %s", ...).',
                node,
            )


class PillowImportChecker(ASTVisitorChecker):
    """Detects direct imports of PIL.

    PIL should be wrapped in a dedicated images module at the correct layer
    (e.g. cmk.gui.utils.images for GUI code).
    """

    @override
    def checker_id(self) -> str:
        return "pillow-import"

    @override
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

    @override
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

    @override
    def checker_id(self) -> str:
        return "pydantic-type-adapter"

    def __init__(self, file_path: Path, repo_root: Path, source_code: str) -> None:
        super().__init__(file_path, repo_root, source_code)
        self._function_depth = 0

    @override
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function_depth += 1
        self.generic_visit(node)
        self._function_depth -= 1

    @override
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function_depth += 1
        self.generic_visit(node)
        self._function_depth -= 1

    @override
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
        return (isinstance(func, ast.Name) and func.id == "TypeAdapter") or (
            isinstance(func, ast.Subscript)
            and isinstance(func.value, ast.Name)
            and func.value.id == "TypeAdapter"
        )


class TarfileOpenReadChecker(ASTVisitorChecker):
    """Detects tarfile.open() / TarFile.open() in read mode."""

    @override
    def checker_id(self) -> str:
        return "tarfile-open-read"

    _EXCLUDED_DIRS = frozenset({"mkp_tool", "tests", "testlib"})

    @override
    def visit_Call(self, node: ast.Call) -> None:
        if self._is_excluded():
            self.generic_visit(node)
            return
        if self._is_tarfile_open(node) and self._is_read_mode(node):
            self.add_error(
                "tarfile.open() in read mode should not be used directly."
                " Use cmk.ccc.tar_archive.open_(bytes|buffer|path)_(streaming|indexed) instead",
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
        return not any(kw.arg == "mode" for kw in node.keywords) and len(node.args) < 2
