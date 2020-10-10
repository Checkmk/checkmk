#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from ast import literal_eval

import pytest  # type: ignore[import]

from cmk.utils.type_defs import ErrorResult, EvalableFloat, OKResult, Result

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


class TestOkResult:
    @pytest.fixture
    def value(self, request):
        return 0

    @pytest.fixture
    def result(self, value):
        return OKResult(value)

    def test_eq(self, result, value):
        assert (result == value) is False
        assert (value == result) is False
        assert (result != value) is True
        assert (value != result) is True

        ok: Result[int, int] = OKResult(value)
        assert (result == ok) is True
        assert (ok == result) is True
        assert (result != ok) is False
        assert (ok != result) is False

        err: Result[int, int] = ErrorResult(value)
        assert (result == err) is False
        assert (err == result) is False
        assert (result != err) is True
        assert (err != result) is True

    def test_ok_accessor(self, result, value):
        assert result.ok == value

    def test_error_accessor(self, result):
        with pytest.raises(ValueError):
            _err = result.error

    def test_is_ok_is_true(self, result):
        assert result.is_ok() is True

    def test_is_error_is_false(self, result):
        assert result.is_error() is False

    def test_cmp_ok(self, result):
        other: Result[int, int] = OKResult(1)
        assert result.ok < other.ok

        assert result != other

        assert result < other
        assert result <= other
        assert result <= OKResult(result.ok)

        assert other > result
        assert other >= result
        assert other >= OKResult(other.ok)

    def test_cmp_err(self, result, value):
        other: Result[int, int] = ErrorResult(value)
        assert result.ok == other.error

        assert result != other

        assert result < other
        assert result <= other

        assert other > result
        assert other >= result

    def test_iter(self, result, value):
        assert list(result) == [value]

    def test_iter_error(self, result):
        assert list(result.iter_error()) == []

    def test_as_optional(self, result):
        assert result.as_optional() == result.ok

    def test_flatten1(self, result):
        nested: Result[Result, Result] = OKResult(result)
        assert nested != result
        assert nested.flatten() == result
        assert nested.flatten() == result.flatten()
        assert nested.flatten() == nested.join()

    def test_flatten2(self, result):
        nested: Result[Result, Result] = OKResult(OKResult(result))
        assert nested != result
        assert nested.flatten() == result
        assert nested.flatten() == result.flatten()
        assert nested.flatten() == nested.join()

    def test_map(self, result):
        ok = "ok"
        assert not isinstance(result.ok, type(ok))

        other = result.map(lambda v: ok)
        assert other != result
        assert other == OKResult(ok)

    def test_map_error(self, result):
        error = "error"
        assert result.map_error(lambda v: error) == result


class TestErrorResult:
    @pytest.fixture
    def value(self, request):
        return 0

    @pytest.fixture
    def result(self, value):
        return ErrorResult(value)

    def test_eq(self, result, value):
        assert (result == value) is False
        assert (value == result) is False
        assert (result != value) is True
        assert (value != result) is True

        ok: Result[int, int] = OKResult(value)
        assert (result == ok) is False
        assert (ok == result) is False
        assert (result != ok) is True
        assert (ok != result) is True

        err: Result[int, int] = ErrorResult(value)
        assert (result == err) is True
        assert (err == result) is True
        assert (result != err) is False
        assert (err != result) is False

    def test_ok_accessor(self, result):
        with pytest.raises(ValueError):
            _ok = result.ok

    def test_error_accessor(self, result, value):
        assert result.error == value

    def test_is_ok_is_false(self, result):
        assert result.is_ok() is False

    def test_is_error_is_true(self, result):
        assert result.is_error() is True

    def test_cmp_err(self, result):
        other: Result[int, int] = ErrorResult(1)
        assert result.error < other.error

        assert result != other

        assert result < other
        assert result <= other
        assert result <= ErrorResult(result.error)

        assert other > result
        assert other >= result
        assert other >= ErrorResult(other.error)

    def test_cmp_ok(self, result, value):
        other: Result[int, int] = OKResult(value)
        assert result.error == other.ok

        assert result != other

        assert result > other
        assert result >= other

        assert other < result
        assert other <= result

    def test_iter(self, result):
        assert list(result) == []

    def test_iter_error(self, result, value):
        assert list(result.iter_error()) == [value]

    def test_as_optional(self, result):
        assert result.as_optional() is None

    def test_flatten1(self, result):
        nested: Result[Result, Result] = ErrorResult(result)
        assert nested != result
        assert nested.flatten() == result
        assert nested.flatten() == result.flatten()
        assert nested.flatten() == nested.join()

    def test_flatten2(self, result):
        nested: Result[Result, Result] = ErrorResult(ErrorResult(result))
        assert nested != result
        assert nested.flatten() == result
        assert nested.flatten() == result.flatten()
        assert nested.flatten() == nested.join()

    def test_map(self, result):
        ok = "ok"
        assert result.map(lambda v: ok) == result

    def test_map_error(self, result):
        error = "error"
        assert not isinstance(result.error, type(error))

        other = result.map_error(lambda v: error)
        assert other != result
        assert other.error == error
