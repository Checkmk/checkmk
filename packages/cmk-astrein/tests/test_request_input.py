#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import Path

from cmk.astrein.checkers.request_input import RequestValidatedInputChecker
from cmk.astrein.framework import CheckerError


def _check(code: str) -> list[CheckerError]:
    checker = RequestValidatedInputChecker(Path("test/test.py"), Path("test"), code)
    return checker.check(ast.parse(code))


def test_direct_userid_from_request_var() -> None:
    code = 'def f():\n    UserId(request.var("x"))'
    errors = _check(code)
    assert len(errors) == 1
    assert "request.get_validated_type_input" in errors[0].message


def test_direct_hostaddress_from_get_str_input() -> None:
    code = 'def f():\n    HostAddress(request.get_str_input("x"))'
    errors = _check(code)
    assert len(errors) == 1


def test_direct_hostname_from_get_str_input_mandatory() -> None:
    code = 'def f():\n    Hostname(request.get_str_input_mandatory("x"))'
    errors = _check(code)
    assert len(errors) == 1


def test_single_hop_var_to_userid() -> None:
    code = 'def f():\n    x = request.var("k")\n    UserId(x)'
    errors = _check(code)
    assert len(errors) == 1


def test_single_hop_with_method_chain() -> None:
    code = 'def f():\n    x = request.get_str_input("k")\n    UserId(x.rstrip())'
    errors = _check(code)
    assert len(errors) == 1


def test_module_level_not_checked() -> None:
    code = 'x = request.var("k")\nUserId(x)'
    assert _check(code) == []


def test_unrelated_variable_ok() -> None:
    code = "def f():\n    x = something_else()\n    UserId(x)"
    assert _check(code) == []


def test_no_source_ok() -> None:
    code = 'def f():\n    UserId("admin")'
    assert _check(code) == []


def test_source_without_sink_ok() -> None:
    code = 'def f():\n    x = request.var("k")\n    print(x)'
    assert _check(code) == []


def test_non_request_receiver_ok() -> None:
    code = 'def f():\n    x = other.var("k")\n    UserId(x)'
    assert _check(code) == []


def test_async_function_detected() -> None:
    code = 'async def f():\n    UserId(request.var("x"))'
    errors = _check(code)
    assert len(errors) == 1
