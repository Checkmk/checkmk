#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import Path

from cmk.astrein.checkers.pydantic_type_adapter import PydanticTypeAdapterChecker
from cmk.astrein.framework import CheckerError


def _check_type_adapter(code: str) -> list[CheckerError]:
    checker = PydanticTypeAdapterChecker(Path("test/test.py"), Path("test"), code)
    return checker.check(ast.parse(code))


def test_type_adapter_rejects_in_function() -> None:
    code = "def f():\n    TypeAdapter(X)"
    errors = _check_type_adapter(code)
    assert len(errors) == 1
    assert "TypeAdapter" in errors[0].message


def test_type_adapter_rejects_subscript_in_function() -> None:
    code = "def f():\n    TypeAdapter[T](X)"
    errors = _check_type_adapter(code)
    assert len(errors) == 1
    assert "TypeAdapter" in errors[0].message


def test_type_adapter_allows_module_level() -> None:
    assert _check_type_adapter("TypeAdapter(X)") == []


def test_type_adapter_allows_other_call_in_function() -> None:
    assert _check_type_adapter("def f():\n    SomeOther(X)") == []


def test_type_adapter_rejects_in_async_function() -> None:
    code = "async def f():\n    TypeAdapter(X)"
    errors = _check_type_adapter(code)
    assert len(errors) == 1


def test_type_adapter_rejects_in_nested_function() -> None:
    code = "def f():\n    def g():\n        TypeAdapter(X)"
    errors = _check_type_adapter(code)
    assert len(errors) == 1


def test_type_adapter_rejects_in_method() -> None:
    code = "class C:\n    def m(self):\n        TypeAdapter(X)"
    errors = _check_type_adapter(code)
    assert len(errors) == 1
