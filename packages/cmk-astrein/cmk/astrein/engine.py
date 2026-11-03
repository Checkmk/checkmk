#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import Path
from typing import Final

from cmk.astrein.framework import CheckerError, CheckerFactory
from cmk.astrein.suppressions import parse_suppressions, Suppression

ENGINE_SUMMARIES: Final = {
    "file-read-error": "File could not be read",
    "syntax-error": "Python syntax error",
    "unused-suppression": "Suppression comment does not suppress anything",
}
"""Summaries of the ids the engine reports itself."""


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
        ran_checker_ids.add(checker.checker_id)
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
