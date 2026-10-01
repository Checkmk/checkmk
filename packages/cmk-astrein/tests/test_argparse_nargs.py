#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import Path

import pytest

from cmk.astrein.checker_argparse_nargs import ArgparseNargsChecker
from cmk.astrein.framework import CheckerError

_REPO_ROOT = Path("/repo")
_AGENT_PATH = Path("/repo/cmk/plugins/foo/special_agent/agent_foo.py")


def _check(code: str, file_path: Path = _AGENT_PATH) -> list[CheckerError]:
    checker = ArgparseNargsChecker(file_path, _REPO_ROOT, code)
    return checker.check(ast.parse(code))


@pytest.mark.parametrize("nargs", ['"*"', '"+"', "2", "argparse.ZERO_OR_MORE"])
def test_flags_multi_value_nargs(nargs: str) -> None:
    errors = _check(f'parser.add_argument("--hosts", nargs={nargs})')
    assert [e.checker_id for e in errors] == ["argparse-nargs"]


@pytest.mark.parametrize("nargs", ['"?"', "0", "1"])
def test_allows_single_value_nargs(nargs: str) -> None:
    assert _check(f'parser.add_argument("--host", nargs={nargs})') == []


def test_allows_positional_nargs() -> None:
    assert _check('parser.add_argument("hosts", nargs="+")') == []


def test_allows_add_argument_without_nargs() -> None:
    assert _check('parser.add_argument("--host", action="append")') == []


def test_reports_line_of_add_argument_call() -> None:
    errors = _check('parser = make()\nparser.add_argument(\n    "--hosts",\n    nargs="+",\n)')
    assert [e.line for e in errors] == [2]


@pytest.mark.parametrize(
    "file_path",
    [
        Path("/repo/cmk/gui/foo.py"),
        Path("/repo/tests/unit/cmk/plugins/foo/test_agent_foo.py"),
        Path("/repo/packages/cmk-plugins/tests/cmk/plugins/foo/test_agent_foo.py"),
        Path("/repo/cmk/plugins/foo/tests/test_agent_foo.py"),
    ],
)
def test_ignores_files_outside_plugins(file_path: Path) -> None:
    assert _check('parser.add_argument("--hosts", nargs="+")', file_path=file_path) == []


@pytest.mark.parametrize(
    "file_path",
    [
        Path("/repo/cmk/plugins/foo/lib/agent.py"),
        Path("/repo/packages/cmk-plugins/cmk/plugins/foo/special_agent/agent_foo.py"),
        Path("/repo/non-free/packages/cmk-plugins-nonfree/cmk/plugins/foo/special_agents/a.py"),
    ],
)
def test_matches_anywhere_below_plugins(file_path: Path) -> None:
    errors = _check('parser.add_argument("--hosts", nargs="+")', file_path=file_path)
    assert len(errors) == 1


def test_honours_suppression() -> None:
    code = 'parser.add_argument("--hosts", nargs="+")  # astrein: disable=argparse-nargs'
    assert _check(code) == []
