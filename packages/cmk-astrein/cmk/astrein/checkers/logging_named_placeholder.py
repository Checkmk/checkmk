#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import override

from cmk.astrein.checkers._placeholders import has_positional_placeholder
from cmk.astrein.framework import ASTVisitorChecker

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

    checker_id = "logging-named-placeholder"
    summary = "Requires named placeholders in logging calls"

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
