#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from typing import override

from cmk.astrein.framework import ASTVisitorChecker


class ABCMetaMetaclassChecker(ASTVisitorChecker):
    """Detects use of `metaclass=ABCMeta` instead of inheriting from ABC."""

    checker_id = "abcmeta-metaclass"
    summary = "Requires inheriting from ABC instead of metaclass=ABCMeta"

    @override
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for keyword in node.keywords:
            if keyword.arg == "metaclass" and self._is_abcmeta(keyword.value):
                self.add_error(
                    "Use `class Foo(ABC):` instead of `metaclass=ABCMeta`",
                    node,
                )
        self.generic_visit(node)

    @staticmethod
    def _is_abcmeta(node: ast.expr) -> bool:
        return (isinstance(node, ast.Name) and node.id == "ABCMeta") or (
            isinstance(node, ast.Attribute)
            and node.attr == "ABCMeta"
            and isinstance(node.value, ast.Name)
            and node.value.id == "abc"
        )
