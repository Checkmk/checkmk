#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import Path

from cmk.astrein.checkers.abcmeta_metaclass import ABCMetaMetaclassChecker
from cmk.astrein.framework import CheckerError


def _check_abcmeta(code: str) -> list[CheckerError]:
    checker = ABCMetaMetaclassChecker(Path("test/test.py"), Path("test"), code)
    return checker.check(ast.parse(code))


def test_abcmeta_rejects_metaclass_abcmeta() -> None:
    errors = _check_abcmeta("class Foo(metaclass=ABCMeta): pass")
    assert len(errors) == 1
    assert "ABC" in errors[0].message


def test_abcmeta_rejects_metaclass_abc_dot_abcmeta() -> None:
    errors = _check_abcmeta("class Foo(metaclass=abc.ABCMeta): pass")
    assert len(errors) == 1
    assert "ABC" in errors[0].message


def test_abcmeta_allows_inheriting_abc() -> None:
    assert _check_abcmeta("class Foo(ABC): pass") == []


def test_abcmeta_allows_inheriting_other_base() -> None:
    assert _check_abcmeta("class Foo(Bar): pass") == []


def test_abcmeta_allows_other_metaclass() -> None:
    assert _check_abcmeta("class Foo(metaclass=SomethingElse): pass") == []
