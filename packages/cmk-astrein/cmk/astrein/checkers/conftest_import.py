#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from typing import override

from cmk.astrein.framework import ASTVisitorChecker


class ConftestImportChecker(ASTVisitorChecker):
    """Detects imports from a conftest module.

    pytest loads conftest modules as plugins and documents them as not importable. Shared
    test code belongs in a testlib module imported by its absolute path.
    """

    checker_id = "conftest-import"
    summary = "Forbids imports from conftest modules"

    @override
    def visit_Import(self, node: ast.Import) -> None:
        if any(_is_conftest(alias.name) for alias in node.names):
            self.add_error(
                "Import of a conftest module. Shared test code belongs in a testlib", node
            )
        self.generic_visit(node)

    @override
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if _is_conftest(node.module or "") or any(alias.name == "conftest" for alias in node.names):
            self.add_error(
                "Import from a conftest module. Shared test code belongs in a testlib", node
            )
        self.generic_visit(node)


def _is_conftest(module: str) -> bool:
    return module == "conftest" or module.endswith(".conftest")
