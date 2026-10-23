#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import PurePosixPath
from typing import override

from cmk.astrein.framework import ASTVisitorChecker


class PillowImportChecker(ASTVisitorChecker):
    """Detects direct imports of PIL.

    PIL should be wrapped in a dedicated images module at the correct layer
    (e.g. cmk.gui.utils.images for GUI code).
    """

    checker_id = "pillow-import"
    summary = "Forbids direct imports of PIL"

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
