#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import PurePosixPath
from typing import override

from cmk.astrein.framework import ASTVisitorChecker


class TarfileOpenReadChecker(ASTVisitorChecker):
    """Detects tarfile.open() / TarFile.open() in read mode."""

    checker_id = "tarfile-open-read"
    summary = "Forbids tarfile.open() in read mode"

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
