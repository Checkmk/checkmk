#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from typing import override

from cmk.astrein.framework import ASTVisitorChecker


class HTMLDebugChecker(ASTVisitorChecker):
    """Detects calls to `html.debug(...)`."""

    checker_id = "html-debug"
    summary = "Forbids html.debug() calls"

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
