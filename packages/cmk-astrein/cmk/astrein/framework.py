#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Base framework for AST-based code quality checkers."""

import ast
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from cmk.astrein.suppressions import parse_suppressions, Suppression


@dataclass(frozen=True)
class CheckerError:
    """Represents a checker violation."""

    message: str
    line: int
    column: int
    file_path: Path
    checker_id: str


class ASTVisitorChecker(ast.NodeVisitor):
    checker_id: ClassVar[str]
    """Unique kebab-case id naming what is checked, for selection, suppressions and reports."""
    summary: ClassVar[str]
    """One-line description of what the checker enforces."""

    def __init__(self, file_path: Path, repo_root: Path, source_code: str):
        self.file_path = file_path
        self.repo_root = repo_root
        self.source_code = source_code
        self.source_lines = source_code.splitlines()
        self.errors: list[CheckerError] = []
        self.suppressions: Sequence[Suppression] = []
        self.used_suppressions: set[Suppression] = set()

    def _find_suppression(self, node: ast.AST) -> Suppression | None:
        line = getattr(node, "lineno", None)
        if line is None:
            return None
        return next((s for s in self.suppressions if s.covers(line)), None)

    def add_error(self, message: str, node: ast.AST) -> None:
        if (suppression := self._find_suppression(node)) is not None:
            self.used_suppressions.add(suppression)
            return

        self.errors.append(
            CheckerError(
                message=message,
                line=node.lineno if hasattr(node, "lineno") else 0,
                column=node.col_offset if hasattr(node, "col_offset") else 0,
                file_path=self.file_path.relative_to(self.repo_root),
                checker_id=self.checker_id,
            )
        )

    def check(
        self, tree: ast.AST, suppressions: Sequence[Suppression] | None = None
    ) -> list[CheckerError]:
        """Record used suppressions; pass ``suppressions`` to share one parse across checkers."""
        if suppressions is None:
            suppressions = parse_suppressions(self.source_code)
        self.suppressions = [s for s in suppressions if s.checker_id == self.checker_id]
        self.used_suppressions = set()
        self.errors = []
        self.visit(tree)
        return self.errors


#: A callable that creates a checker for a given file.
#: Checker classes satisfy this directly; use ``functools.partial`` to bind
#: extra arguments (e.g. a pre-loaded config) before passing to ``run_checkers``.
CheckerFactory = Callable[[Path, Path, str], ASTVisitorChecker]
