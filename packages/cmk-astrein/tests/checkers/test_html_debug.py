#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import Path

from cmk.astrein.checkers.html_debug import HTMLDebugChecker
from cmk.astrein.framework import CheckerError


def _check_html_debug(code: str) -> list[CheckerError]:
    checker = HTMLDebugChecker(Path("test/test.py"), Path("test"), code)
    return checker.check(ast.parse(code))


def test_html_debug_rejects_call_with_args() -> None:
    errors = _check_html_debug("html.debug(x)")
    assert len(errors) == 1
    assert "html.debug" in errors[0].message


def test_html_debug_rejects_call_without_args() -> None:
    errors = _check_html_debug("html.debug()")
    assert len(errors) == 1
    assert "html.debug" in errors[0].message


def test_html_debug_allows_other_html_methods() -> None:
    assert _check_html_debug("html.render()") == []


def test_html_debug_allows_debug_on_other_objects() -> None:
    assert _check_html_debug("foo.debug()") == []


def test_html_debug_allows_bare_debug_call() -> None:
    assert _check_html_debug("debug()") == []
