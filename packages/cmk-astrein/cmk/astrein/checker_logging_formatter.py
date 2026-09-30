#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import override

from cmk.astrein.framework import ASTVisitorChecker
from cmk.astrein.module_layers_config import compute_module_name

#: Repo-relative glob patterns (``PurePosixPath.full_match``) the checker skips.
_EXCLUDED_GLOBS = (
    # Agent-side code ships to monitored hosts as standalone scripts and cannot import
    # cmk.ccc; same globs as the Python-compat per-file-ignores in pyproject.toml.
    "agents/plugins/*",
    "**/cmk/plugins/*/agents/*",
    "non-free/packages/cmk-update-agent/**",
    # Cannot import cmk.ccc; they log via cmk.server_side_programs.v1.configure_logging.
    "packages/cmk-plugins/**",
    "packages/cmk-plugin-apis/**",
    "**/tests/**",
    "**/testlib/**",
    "doc/**",  # standalone example scripts for customers, also excluded from ruff
    "packages/cmk-astrein/**",  # may import nothing else, see module_layers.toml
)

#: Repo-relative glob patterns force-checked even when they match an ``_EXCLUDED_GLOBS``
#: entry, so individual files can be migrated ahead of their surrounding tree.
_INCLUDED_GLOBS: tuple[str, ...] = ()

#: Fully qualified name of the formatter every Checkmk log handler must use.
_CMKFORMATTER = "cmk.ccc.log.CMKFormatter"
_CMKFORMATTER_CLASS = _CMKFORMATTER.rpartition(".")[2]
_LOGGING_FORMATTER = "logging.Formatter"
_LOGGING_BASIC_CONFIG = "logging.basicConfig"
_BASIC_CONFIG_FORMAT_KEYWORDS = frozenset({"format", "datefmt"})
_DICT_CONFIG_FORMAT_KEYS = frozenset({"format", "fmt", "datefmt", "class"})


class LoggingFormatterChecker(ASTVisitorChecker):
    """Requires every log handler to format via ``cmk.ccc.log.CMKFormatter``.

    Constructing a ``logging.Formatter``, handing a format to ``logging.basicConfig``, or
    building a ``dictConfig`` formatter from anything but ``CMKFormatter`` lets a
    component's log lines drift from the shared format.

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
        self._module_name = str(compute_module_name(file_path, repo_root))
        self._imported_names: dict[str, str] = {}

    @override
    def checker_id(self) -> str:
        return "logging-formatter"

    @override
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.asname is None:
                # `import logging.config` binds the top-level package name.
                top_level = alias.name.partition(".")[0]
                self._imported_names[top_level] = top_level
            else:
                self._imported_names[alias.asname] = alias.name
        self.generic_visit(node)

    @override
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level == 0 and node.module is not None:
            for alias in node.names:
                self._imported_names[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        self.generic_visit(node)

    @override
    def visit_Call(self, node: ast.Call) -> None:
        if self._is_included():
            if self._qualified_name(node.func) == _LOGGING_FORMATTER:
                self.add_error(
                    f"Do not construct logging.Formatter. Use {_CMKFORMATTER} so all "
                    f"Checkmk logs share one format; {_CMKFORMATTER_CLASS}(message_only=True) "
                    "renders the bare message for interactive console output.",
                    node,
                )
            elif self._qualified_name(node.func) == _LOGGING_BASIC_CONFIG and any(
                kw.arg in _BASIC_CONFIG_FORMAT_KEYWORDS for kw in node.keywords
            ):
                self.add_error(
                    "Do not pass format= or datefmt= to logging.basicConfig. Build the handler "
                    f"yourself, call handler.setFormatter({_CMKFORMATTER}()) and pass "
                    "handlers=[handler] to basicConfig.",
                    node,
                )
        self.generic_visit(node)

    @override
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if self._is_included() and f"{self._module_name}.{node.name}" != _CMKFORMATTER:
            for base in node.bases:
                if self._qualified_name(base) == _LOGGING_FORMATTER:
                    self.add_error(
                        f"Do not subclass logging.Formatter. Subclass {_CMKFORMATTER} "
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
            formatter_entries = _string_keyed_entries(formatter)
            # A dotted-path string resolves only at runtime, so it would hide a rename.
            if (
                (factory := formatter_entries.get("()")) is None
                or self._qualified_name(factory) != _CMKFORMATTER
                or formatter_entries.keys() & _DICT_CONFIG_FORMAT_KEYS
            ):
                self.add_error(
                    f"dictConfig formatters must be built by {_CMKFORMATTER}: import the "
                    f'class, pass it as "()": {_CMKFORMATTER_CLASS} and drop the '
                    "format/fmt/datefmt/class keys.",
                    formatter,
                )

    def _qualified_name(self, node: ast.expr) -> str | None:
        """Resolve a name or attribute chain through the file's imports."""
        if isinstance(node, ast.Name):
            return self._imported_names.get(node.id)
        if isinstance(node, ast.Attribute) and (base := self._qualified_name(node.value)):
            return f"{base}.{node.attr}"
        return None

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


def _string_keyed_entries(node: ast.Dict) -> dict[str, ast.expr]:
    return {
        key.value: value
        for key, value in zip(node.keys, node.values, strict=True)
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    }
