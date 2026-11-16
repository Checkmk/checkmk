#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import Path
from typing import override

import pytest

from cmk.astrein.framework import ASTVisitorChecker

_REPO_ROOT = Path("/repo")


class _VisitRecordingChecker(ASTVisitorChecker):
    checker_id = "visit-recording"
    summary = "Records whether it visited the module"
    excluded_globs = frozenset({"excluded/**"})
    visited = False

    @override
    def visit_Module(self, node: ast.Module) -> None:
        self.visited = True


@pytest.mark.parametrize(
    "relative_path, expected_visited",
    [
        ("excluded/module.py", False),
        ("checked/module.py", True),
    ],
)
def test_skips_files_matching_excluded_glob(relative_path: str, expected_visited: bool) -> None:
    checker = _VisitRecordingChecker(_REPO_ROOT / relative_path, _REPO_ROOT)

    checker.check(ast.parse(""), [])

    assert checker.visited is expected_visited
