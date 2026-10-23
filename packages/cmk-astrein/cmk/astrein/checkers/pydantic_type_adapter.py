#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import Path
from typing import override

from cmk.astrein.framework import ASTVisitorChecker


class PydanticTypeAdapterChecker(ASTVisitorChecker):
    """Detects TypeAdapter() calls inside function/method bodies (module-level is fine)."""

    checker_id = "pydantic-type-adapter"
    summary = "Flags TypeAdapter() construction inside functions"

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
