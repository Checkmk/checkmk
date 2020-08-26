#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from ast import literal_eval

import pytest  # type: ignore[import]

from cmk.utils.type_defs import EvalableFloat, Result

from cmk.snmplib.type_defs import OIDBytes, OIDSpec


@pytest.mark.parametrize("value", [3, ("foo", "bar")])
def test_oidspec_invalid_type(value):
    with pytest.raises(TypeError):
        _ = OIDSpec(value)


@pytest.mark.parametrize("value", ["", "foo", "1."])
def test_oidspec_invalid_value(value):
    with pytest.raises(ValueError):
        _ = OIDSpec(value)


@pytest.mark.parametrize("value", ["foo", 1])
def test_oidspec_invalid_adding_type(value):
    oid = OIDSpec(".1.2.3")
    with pytest.raises(TypeError):
        _ = oid + value


@pytest.mark.parametrize("left, right", [
    (OIDBytes("4.5"), OIDBytes("4.5")),
    (OIDSpec(".1.2.3"), OIDSpec(".1.2.3")),
])
def test_oidspec_invalid_adding_value(left, right):
    with pytest.raises(ValueError):
        _ = left + right


def test_oidspec():
    oid_base = OIDSpec(".1.2.3")
    oid_column = OIDBytes("4.5")

    assert str(oid_base) == ".1.2.3"
    assert str(oid_column) == "4.5"

    assert repr(oid_base) == "OIDSpec('.1.2.3')"
    assert repr(oid_column) == "OIDBytes('4.5')"

    oid_sum = oid_base + oid_column
    assert isinstance(oid_sum, OIDBytes)
    assert str(oid_sum) == ".1.2.3.4.5"


def test_evalable_float():
    inf = EvalableFloat('inf')
    assert literal_eval("%r" % inf) == float('inf')


class TestOKResult:
    @pytest.fixture(params=[None, 0])
    def value(self, request):
        return request.param

    @pytest.fixture
    def result(self, value):
        return Result.OK(value)

    def test_eq(self, result, value):
        assert (result == value) is False
        assert (value == result) is False
        assert (result != value) is True
        assert (value != result) is True

        ok = Result.OK(value)
        assert (result == ok) is True
        assert (ok == result) is True
        assert (result != ok) is False
        assert (ok != result) is False

        err = Result.Err(value)
        assert (result == err) is False
        assert (err == result) is False
        assert (result != err) is True
        assert (err != result) is True

    def test_ok_accessor(self, result, value):
        assert result.ok == value

    def test_err_accessor(self, result):
        assert not result.err
        assert result.err is None

    def test_is_ok_is_true(self, result):
        assert result.is_ok() is True

    def test_is_err_is_false(self, result):
        assert result.is_err() is False

    def test_unwrap_ok_produces_ok_value(self, result, value):
        assert result.unwrap_ok() == value

    def test_unwrap_err_raises_valueerror(self, result, value):
        with pytest.raises(ValueError) as excinfo:
            result.unwrap_err()

        assert str(excinfo.value) == str(value)


class TestErrResult:
    @pytest.fixture(params=["error message"])
    def value(self, request):
        return request.param

    @pytest.fixture
    def result(self, value):
        return Result.Err(value)

    def test_eq(self, result, value):
        assert (result == value) is False
        assert (value == result) is False
        assert (result != value) is True
        assert (value != result) is True

        ok = Result.OK(value)
        assert (result == ok) is False
        assert (ok == result) is False
        assert (result != ok) is True
        assert (ok != result) is True

        err = Result.Err(value)
        assert (result == err) is True
        assert (err == result) is True
        assert (result != err) is False
        assert (err != result) is False

    def test_ok_accessor(self, result):
        assert not result.ok
        assert result.ok is None

    def test_err_accessor(self, result, value):
        assert result.err == value

    def test_is_ok_is_false(self, result):
        assert result.is_ok() is False

    def test_is_err_is_true(self, result):
        assert result.is_err() is True

    def test_unwrap_ok_raises_valueerror(self, result, value):
        with pytest.raises(ValueError) as excinfo:
            result.unwrap_ok()

        assert str(excinfo.value) == str(value)

    def test_unwrap_err_produces_err_value(self, result, value):
        assert result.unwrap_err() == value
