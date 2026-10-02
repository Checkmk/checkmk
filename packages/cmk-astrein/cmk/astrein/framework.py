#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Base framework for AST-based code quality checkers."""

import ast
import io
import re
import tokenize
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import override


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

    @override
    def __str__(self) -> str:
        return self.format_gcc()


_SUPPRESSION_PATTERN = re.compile(r"astrein: disable=([\w-]+)")


@dataclass(frozen=True)
class Suppression:
    """An inline ``# astrein: disable=<checker-id>`` comment."""

    checker_id: str
    line: int
    column: int
    covers_next_line: bool

    def covers(self, line: int) -> bool:
        return line == self.line or (self.covers_next_line and line == self.line + 1)


def parse_suppressions(source_code: str) -> Sequence[Suppression]:
    """Find all suppressions in actual comments, ignoring look-alikes in strings."""
    return [
        Suppression(
            checker_id=match.group(1),
            line=token.start[0],
            column=token.start[1] + match.start(),
            covers_next_line=not token.line[: token.start[1]].strip(),
        )
        for token in tokenize.generate_tokens(io.StringIO(source_code).readline)
        if token.type == tokenize.COMMENT
        for match in _SUPPRESSION_PATTERN.finditer(token.string)
    ]


class ASTVisitorChecker(ABC, ast.NodeVisitor):
    def __init__(self, file_path: Path, repo_root: Path, source_code: str):
        self.file_path = file_path
        self.repo_root = repo_root
        self.source_code = source_code
        self.source_lines = source_code.splitlines()
        self.errors: list[CheckerError] = []
        self.suppressions: Sequence[Suppression] = []
        self.used_suppressions: set[Suppression] = set()

    @abstractmethod
    def checker_id(self) -> str:
        """Return unique identifier for this checker."""
        ...

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
                checker_id=self.checker_id(),
            )
        )

    def check(
        self, tree: ast.AST, suppressions: Sequence[Suppression] | None = None
    ) -> list[CheckerError]:
        """Record used suppressions; pass ``suppressions`` to share one parse across checkers."""
        if suppressions is None:
            suppressions = parse_suppressions(self.source_code)
        self.suppressions = [s for s in suppressions if s.checker_id == self.checker_id()]
        self.used_suppressions = set()
        self.errors = []
        self.visit(tree)
        return self.errors


#: A callable that creates a checker for a given file.
#: Checker classes satisfy this directly; use ``functools.partial`` to bind
#: extra arguments (e.g. a pre-loaded config) before passing to ``run_checkers``.
CheckerFactory = Callable[[Path, Path, str], ASTVisitorChecker]


def run_checkers(
    file_path: Path,
    repo_root: Path,
    checker_factories: list[CheckerFactory],
    *,
    source_code: str | None = None,
    report_unknown_suppressions: bool = False,
) -> list[CheckerError]:
    """Run multiple checkers on a Python file.

    Each factory is called with ``(file_path, repo_root, source_code)``
    to produce a checker instance.  Plain checker classes work as factories;
    use ``functools.partial`` to pre-bind extra parameters.

    Pass ``source_code`` to check content that differs from the file on disk,
    e.g. an unsaved editor buffer.

    Unused suppressions are reported only for checkers that ran. Pass
    ``report_unknown_suppressions`` when the factories cover all checkers to
    also report suppressions naming an unknown checker.
    """
    if source_code is None:
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

    suppressions = parse_suppressions(source_code)
    all_errors: list[CheckerError] = []
    ran_checker_ids: set[str] = set()
    used_suppressions: set[Suppression] = set()
    for factory in checker_factories:
        checker = factory(file_path, repo_root, source_code)
        all_errors.extend(checker.check(tree, suppressions))
        ran_checker_ids.add(checker.checker_id())
        used_suppressions |= checker.used_suppressions

    for suppression in suppressions:
        if suppression in used_suppressions:
            continue
        if suppression.checker_id in ran_checker_ids:
            message = f"Unused suppression for {suppression.checker_id}: nothing to suppress"
        elif report_unknown_suppressions:
            message = f"Unused suppression for unknown checker {suppression.checker_id}"
        else:
            continue
        all_errors.append(
            CheckerError(
                message=message,
                line=suppression.line,
                column=suppression.column,
                file_path=file_path.relative_to(repo_root),
                checker_id="unused-suppression",
            )
        )

    return all_errors
