#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

import cmk.gui.valuespec as vs
from cmk.gui.exceptions import MKUserError

from .utils import expect_validate_failure, expect_validate_success, request_var

# size is only relevant for html input element


def test_integer_valuespec_validate() -> None:
    expect_validate_failure(vs.Integer(), "asd")  # type:ignore
    expect_validate_success(vs.Integer(), 128)
    expect_validate_success(vs.Integer(minvalue=10, maxvalue=300), 128)
    expect_validate_failure(vs.Integer(minvalue=10, maxvalue=300), 333)
    expect_validate_failure(vs.Integer(minvalue=10, maxvalue=300), 9)


def test_integer_valuespec_default_value() -> None:
    assert vs.Integer().default_value() == 0
    assert vs.Integer(minvalue=10).default_value() == 10
    assert vs.Integer(default_value=99).default_value() == 99
    assert vs.Integer(default_value=99, minvalue=10).default_value() == 99
    assert vs.Integer(default_value=lambda: 77).default_value() == 77
    assert vs.Integer(default_value=lambda: 77, minvalue=10).default_value() == 77


def test_integer_valuespec_canonical_value() -> None:
    assert vs.Integer().canonical_value() == 0
    assert vs.Integer(minvalue=10).canonical_value() == 10
    assert vs.Integer(default_value=99).canonical_value() == 0
    assert vs.Integer(default_value=99, minvalue=10).canonical_value() == 10
    assert vs.Integer(default_value=lambda: 77).canonical_value() == 0
    assert vs.Integer(default_value=lambda: 77, minvalue=10).canonical_value() == 10


def test_integer_valuespec_from_html_vars() -> None:
    with request_var(integer="123"):
        assert vs.Integer().from_html_vars("integer") == 123

    with request_var(integer="asd"):
        with pytest.raises(MKUserError):
            vs.Integer().from_html_vars("integer")


def test_integer_valuespec_value_to_html() -> None:
    assert vs.Integer().value_to_html(123) == "123"
    assert vs.Integer(thousand_sep=".", unit="unit").value_to_html(1002003) == "1.002.003 unit"


def test_integer_valuespec_json() -> None:
    assert vs.Integer().value_from_json(vs.Integer().value_to_json(10)) == 10
    assert vs.Integer().value_from_json(11.0) == 11
    assert vs.Integer().value_to_json(12) == 12


def test_integer_valuespec_mask() -> None:
    assert vs.Integer().mask(13) == 13
