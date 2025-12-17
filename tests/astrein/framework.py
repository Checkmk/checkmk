#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Base framework for AST-based code quality checkers."""

from __future__ import annotations

import ast
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CheckerError:
    """Represents a checker violation."""

    message: str
    line: int
    column: int
    file_path: Path
    checker_id: str

    def format_gcc(self) -> str:
        """Format error in GCC-style for IDE/Bazel integration."""
        return (
            f"{self.file_path}:{self.line}:{self.column}: error: [{self.checker_id}] {self.message}"
        )

    def __str__(self) -> str:
        return self.format_gcc()


class ASTVisitorChecker(ABC, ast.NodeVisitor):
    def __init__(self, file_path: Path, repo_root: Path, source_code: str):
        self.file_path = file_path
        self.repo_root = repo_root
        self.source_code = source_code
        self.source_lines = source_code.splitlines()
        self.errors: list[CheckerError] = []

    @abstractmethod
    def checker_id(self) -> str:
        """Return unique identifier for this checker."""
        ...

    def _is_suppressed(self, node: ast.AST) -> bool:
        if not hasattr(node, "lineno") or node.lineno is None:
            return False

        line_idx = node.lineno - 1
        if line_idx < 0 or line_idx >= len(self.source_lines):
            return False

        current_line = self.source_lines[line_idx]
        if f"pylint: disable={self.checker_id()}" in current_line:
            return True

        if line_idx > 0:
            prev_line = self.source_lines[line_idx - 1]
            if (
                prev_line.strip().startswith("#")
                and f"pylint: disable={self.checker_id()}" in prev_line
            ):
                return True

        return False

    def add_error(self, message: str, node: ast.AST) -> None:
        if self._is_suppressed(node):
            return

        self.errors.append(
            CheckerError(
                message=message,
                line=node.lineno if hasattr(node, "lineno") else 0,
                column=node.col_offset if hasattr(node, "col_offset") else 0,
                file_path=self.file_path.relative_to(self.repo_root),
                checker_id=self.checker_id(),
            )
        )

    def check(self, tree: ast.AST) -> list[CheckerError]:
        self.errors = []
        self.visit(tree)
        return self.errors


def run_checkers(
    file_path: Path, repo_root: Path, checker_classes: list[type[ASTVisitorChecker]]
) -> list[CheckerError]:
    """Run multiple checkers on a Python file"""
    try:
        source_code = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        # Return a synthetic error if we can't read the file
        return [
            CheckerError(
                message=f"Failed to read file: {e}",
                line=0,
                column=0,
                file_path=file_path.relative_to(repo_root),
                checker_id="file-read-error",
            )
        ]

    try:
        tree = ast.parse(source_code, filename=str(file_path))
    except SyntaxError as e:
        # Return a synthetic error for syntax errors
        return [
            CheckerError(
                message=f"Syntax error: {e.msg}",
                line=e.lineno or 0,
                column=e.offset or 0,
                file_path=file_path.relative_to(repo_root),
                checker_id="syntax-error",
            )
        ]

    all_errors: list[CheckerError] = []
    for checker_class in checker_classes:
        checker = checker_class(file_path, repo_root, source_code)
        errors = checker.check(tree)
        all_errors.extend(errors)

    return all_errors
