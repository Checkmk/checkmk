#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import ast
from typing import override

from cmk.astrein.framework import ASTVisitorChecker

_SOURCE_METHODS = frozenset({"var", "get_str_input", "get_str_input_mandatory"})
_SINK_NAMES = frozenset({"UserId", "HostAddress", "Hostname"})

_MESSAGE = (
    "`Hostname`/`UserId`/`HostAddress` raise ValueError which causes crashes"
    " if not caught properly. Use `request.get_validated_type_input` instead."
)


def _is_source_call(node: ast.expr) -> bool:
    """Check if node is request.var/get_str_input/get_str_input_mandatory(...)."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in _SOURCE_METHODS
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "request"
    )


def _is_sink_call(node: ast.Call) -> bool:
    """Check if node is UserId/HostAddress/Hostname(...)."""
    return isinstance(node.func, ast.Name) and node.func.id in _SINK_NAMES


def _contains_name(node: ast.expr, names: frozenset[str]) -> bool:
    """Check if an expression contains any of the given variable names."""
    if isinstance(node, ast.Name):
        return node.id in names
    return any(isinstance(child, ast.Name) and child.id in names for child in ast.walk(node))


class RequestValidatedInputChecker(ASTVisitorChecker):
    """Detects request.var/get_str_input/get_str_input_mandatory values flowing into
    UserId/HostAddress/Hostname constructors within the same function."""

    @override
    def checker_id(self) -> str:
        return "use-request-getvalidatedinputtype"

    @override
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function_body(node)
        self.generic_visit(node)

    @override
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function_body(node)
        self.generic_visit(node)

    def _check_function_body(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        # Pass 1: collect tainted variable names from simple assignments
        tainted: set[str] = set()
        for node in ast.walk(func_node):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and _is_source_call(node.value)
            ):
                tainted.add(node.targets[0].id)

        # Pass 2: find sink calls with tainted arguments
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call) and _is_sink_call(node):
                for arg in node.args:
                    if _is_source_call(arg) or (
                        tainted and _contains_name(arg, frozenset(tainted))
                    ):
                        self.add_error(_MESSAGE, node)
                        break
