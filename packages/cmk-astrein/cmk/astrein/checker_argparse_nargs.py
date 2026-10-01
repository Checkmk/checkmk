#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import ast
from pathlib import Path, PurePosixPath
from typing import override

from cmk.astrein.framework import ASTVisitorChecker


class ArgparseNargsChecker(ASTVisitorChecker):
    """Detects argparse nargs for multi-value arguments in plugin code.

    Using ``nargs`` (``"*"``, ``"+"``, ``argparse.REMAINDER`` or an integer > 1) to
    consume multiple values after a single flag enables argument injection: a
    user-controlled value like ``--malicious`` is silently swallowed by argparse as a
    positional token. Non-literal ``nargs`` values are flagged as well, to be safe.

    The safe alternative is ``action="append"``, with one ``--flag`` per value.

    Allowed exceptions:
    * ``nargs`` consuming at most one value per flag (``"?"``, ``0``, ``1``).
    * positional arguments — safe when the server emits ``"--"`` before them.
    """

    def __init__(self, file_path: Path, repo_root: Path, source_code: str) -> None:
        super().__init__(file_path, repo_root, source_code)
        self._is_plugin_file = self._compute_is_plugin_file()

    @override
    def checker_id(self) -> str:
        return "argparse-nargs"

    @override
    def visit_Call(self, node: ast.Call) -> None:
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
            and self._is_plugin_file
            and not self._is_positional_arg(node)
            and any(kw.arg == "nargs" and _is_multi_value(kw.value) for kw in node.keywords)
        ):
            self.add_error(
                "Unsafe argparse nargs. Use action='append' instead of nargs='*'/'+'/N (N>1).",
                node,
            )
        self.generic_visit(node)

    def _compute_is_plugin_file(self) -> bool:
        parts = PurePosixPath(self.file_path.relative_to(self.repo_root)).parts
        if "tests" in parts[:-1]:
            return False
        return any(
            part == "cmk" and next_part == "plugins"
            for part, next_part in zip(parts[:-2], parts[1:-1])
        )

    @staticmethod
    def _is_positional_arg(node: ast.Call) -> bool:
        if not node.args:
            return False
        first_arg = node.args[0]
        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            return not first_arg.value.startswith("-")
        return False


def _is_multi_value(value: ast.expr) -> bool:
    if not isinstance(value, ast.Constant):
        return True  # argparse.ZERO_OR_MORE, variables, ...: be conservative
    v = value.value
    return v in ("*", "+") or (isinstance(v, int) and not isinstance(v, bool) and v > 1)
