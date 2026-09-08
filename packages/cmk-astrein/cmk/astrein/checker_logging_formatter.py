#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import override

from cmk.astrein.framework import ASTVisitorChecker

#: Repo-relative glob patterns (``PurePosixPath.full_match``) the checker skips.
_EXCLUDED_GLOBS = (
    # Agent-side code ships to monitored hosts as standalone scripts and cannot import
    # cmk.ccc; same globs as the Python-compat per-file-ignores in pyproject.toml.
    "agents/plugins/*",
    "**/cmk/plugins/*/agents/*",
    "non-free/packages/cmk-update-agent/**",
    "**/tests/**",
    "**/testlib/**",
    "doc/**",  # standalone example scripts for customers, also excluded from ruff
    "packages/cmk-astrein/**",  # may import nothing else, see module_layers.toml
)

#: Repo-relative glob patterns force-checked even when they match an ``_EXCLUDED_GLOBS``
#: entry, so individual files can be migrated ahead of their surrounding tree.
_INCLUDED_GLOBS: tuple[str, ...] = ()

_FORMATTER = "Formatter"
_BASIC_CONFIG = "basicConfig"
_CMKFORMATTER_NAME = "CMKFormatter"
_CMKFORMATTER_DEFINITION = "packages/cmk-ccc/cmk/ccc/log.py"
_BASIC_CONFIG_FORMAT_KEYWORDS = frozenset({"format", "datefmt"})
_DICT_CONFIG_FORMAT_KEYS = frozenset({"format", "fmt", "datefmt", "class"})


class LoggingFormatterChecker(ASTVisitorChecker):
    """Requires every log handler to format via ``cmk.ccc.log.CMKFormatter``.

    Constructing a ``logging.Formatter``, or handing a format to ``logging.basicConfig``
    or a ``dictConfig`` mapping, lets a component's log lines drift from the shared format.

    Naming ``logging.Formatter`` in annotations or ``isinstance`` checks is fine: the rule
    bans constructing a formatter, not the type.
    """

    def __init__(
        self,
        file_path: Path,
        repo_root: Path,
        source_code: str,
        *,
        excluded_globs: Sequence[str] = _EXCLUDED_GLOBS,
        included_globs: Sequence[str] = _INCLUDED_GLOBS,
    ) -> None:
        super().__init__(file_path, repo_root, source_code)
        self._excluded_globs = excluded_globs
        self._included_globs = included_globs
        self._logging_names: set[str] = set()
        self._formatter_names: set[str] = set()
        self._basic_config_names: set[str] = set()

    @override
    def checker_id(self) -> str:
        return "logging-formatter"

    @override
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "logging":
                self._logging_names.add(alias.asname or "logging")
            elif alias.name.startswith("logging.") and alias.asname is None:
                # `import logging.config` binds the top-level package name.
                self._logging_names.add("logging")
        self.generic_visit(node)

    @override
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "logging":
            for alias in node.names:
                if alias.name == _FORMATTER:
                    self._formatter_names.add(alias.asname or alias.name)
                elif alias.name == _BASIC_CONFIG:
                    self._basic_config_names.add(alias.asname or alias.name)
        self.generic_visit(node)

    @override
    def visit_Call(self, node: ast.Call) -> None:
        if self._is_included():
            if self._resolves_to(node.func, _FORMATTER, self._formatter_names):
                self.add_error(
                    "Do not construct logging.Formatter. Use cmk.ccc.log.CMKFormatter so all "
                    "Checkmk logs share one format; CMKFormatter(message_only=True) renders "
                    "the bare message for interactive console output.",
                    node,
                )
            elif self._resolves_to(node.func, _BASIC_CONFIG, self._basic_config_names) and any(
                kw.arg in _BASIC_CONFIG_FORMAT_KEYWORDS for kw in node.keywords
            ):
                self.add_error(
                    "Do not pass format= or datefmt= to logging.basicConfig. Build the handler "
                    "yourself, call handler.setFormatter(cmk.ccc.log.CMKFormatter()) and pass "
                    "handlers=[handler] to basicConfig.",
                    node,
                )
        self.generic_visit(node)

    @override
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if self._is_included() and not self._defines_cmk_formatter(node):
            for base in node.bases:
                if self._resolves_to(base, _FORMATTER, self._formatter_names):
                    self.add_error(
                        "Do not subclass logging.Formatter. Subclass cmk.ccc.log.CMKFormatter "
                        "instead so the shared Checkmk log format stays the base of every "
                        "formatter.",
                        node,
                    )
        self.generic_visit(node)

    @override
    def visit_Dict(self, node: ast.Dict) -> None:
        if self._is_included():
            self._check_dict_config(node)
        self.generic_visit(node)

    def _check_dict_config(self, node: ast.Dict) -> None:
        entries = _string_keyed_entries(node)
        # Catches formatters declared as data in a logging.config.dictConfig mapping
        # (version + formatters) instead of constructed in code; uvicorn's log_config
        # and gunicorn's logconfig_dict are the same schema.
        if "version" not in entries or not isinstance(
            formatters := entries.get("formatters"), ast.Dict
        ):
            return
        for formatter in formatters.values:
            if not isinstance(formatter, ast.Dict):
                continue
            keys = _string_keyed_entries(formatter).keys()
            if "()" not in keys or keys & _DICT_CONFIG_FORMAT_KEYS:
                self.add_error(
                    "dictConfig formatters must be built by cmk.ccc.log.CMKFormatter: use "
                    '"()": "cmk.ccc.log.CMKFormatter" (or a subclass of it) and drop the '
                    "format/fmt/datefmt/class keys.",
                    formatter,
                )

    def _resolves_to(self, node: ast.expr, attr: str, direct_names: set[str]) -> bool:
        if isinstance(node, ast.Name):
            return node.id in direct_names
        return (
            isinstance(node, ast.Attribute)
            and node.attr == attr
            and isinstance(node.value, ast.Name)
            and node.value.id in self._logging_names
        )

    def _relative_path(self) -> PurePosixPath | None:
        try:
            return PurePosixPath(self.file_path.relative_to(self.repo_root))
        except ValueError:
            return None

    def _is_included(self) -> bool:
        relative_path = self._relative_path()
        if relative_path is None:
            return True
        if any(relative_path.full_match(glob) for glob in self._included_globs):
            return True
        return not any(relative_path.full_match(glob) for glob in self._excluded_globs)

    def _defines_cmk_formatter(self, node: ast.ClassDef) -> bool:
        return node.name == _CMKFORMATTER_NAME and self._relative_path() == PurePosixPath(
            _CMKFORMATTER_DEFINITION
        )


def _string_keyed_entries(node: ast.Dict) -> dict[str, ast.expr]:
    return {
        key.value: value
        for key, value in zip(node.keys, node.values, strict=True)
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    }
