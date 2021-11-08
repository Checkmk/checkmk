#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.utils.type_defs.result import Error, OK, Result


class TestOk:
    @pytest.fixture
    def value(self, request):
        return 0

    @pytest.fixture
    def result(self, value):
        return OK(value)

    def test_bad_nesting(self, result):
        with pytest.raises(TypeError):
            Error(result)

    def test_eq(self, result, value):
        assert (result == value) is False
        assert (value == result) is False
        assert (result != value) is True
        assert (value != result) is True

        ok: Result[int, int] = OK(value)
        assert (result == ok) is True
        assert (ok == result) is True
        assert (result != ok) is False
        assert (ok != result) is False

        err: Result[int, int] = Error(value)
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
        other: Result[int, int] = OK(1)
        assert result.ok < other.ok

        assert result != other

        assert result < other
        assert result <= other
        assert result <= OK(result.ok)

        assert other > result
        assert other >= result
        assert other >= OK(other.ok)

    def test_cmp_err(self, result, value):
        other: Result[int, int] = Error(value)
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
        nested: Result[Result, Result] = OK(result)
        assert nested != result
        assert nested.flatten() == result
        assert nested.flatten() == result.flatten()
        assert nested.flatten() == nested.join()

    def test_flatten2(self, result):
        nested: Result[Result, Result] = OK(OK(result))
        assert nested != result
        assert nested.flatten() == result
        assert nested.flatten() == result.flatten()
        assert nested.flatten() == nested.join()

    def test_bind_ok(self, result):
        ok: Result[str, str] = OK("ok")
        assert result.ok != ok.ok

        other = result.bind(lambda v: ok)
        assert other != result
        assert other == ok

    def test_bind_error(self, result):
        error: Result[str, str] = Error("error")

        other = result.bind(lambda v: error)
        assert other != result
        assert other == error

    def test_map(self, result):
        ok = "ok"
        assert not isinstance(result.ok, type(ok))

        other = result.map(lambda v: ok)
        assert other != result
        assert other == OK(ok)

    def test_map_error(self, result):
        error = "error"
        assert result.map_error(lambda v: error) == result

    def test_fold(self, result):
        ok = lambda ok_: "ok"
        error = lambda err_: "error"
        assert result.fold(ok=ok, error=error) == "ok"


class TestError:
    @pytest.fixture
    def value(self, request):
        return 0

    @pytest.fixture
    def result(self, value):
        return Error(value)

    def test_bad_nesting(self, result):
        with pytest.raises(TypeError):
            OK(result)

    def test_eq(self, result, value):
        assert (result == value) is False
        assert (value == result) is False
        assert (result != value) is True
        assert (value != result) is True

        ok: Result[int, int] = OK(value)
        assert (result == ok) is False
        assert (ok == result) is False
        assert (result != ok) is True
        assert (ok != result) is True

        err: Result[int, int] = Error(value)
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
        other: Result[int, int] = Error(1)
        assert result.error < other.error

        assert result != other

        assert result < other
        assert result <= other
        assert result <= Error(result.error)

        assert other > result
        assert other >= result
        assert other >= Error(other.error)

    def test_cmp_ok(self, result, value):
        other: Result[int, int] = OK(value)
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
        nested: Result[Result, Result] = Error(result)
        assert nested != result
        assert nested.flatten() == result
        assert nested.flatten() == result.flatten()
        assert nested.flatten() == nested.join()

    def test_flatten2(self, result):
        nested: Result[Result, Result] = Error(Error(result))
        assert nested != result
        assert nested.flatten() == result
        assert nested.flatten() == result.flatten()
        assert nested.flatten() == nested.join()

    def test_bind_ok(self, result):
        ok: Result[str, str] = OK("ok")

        other = result.bind(lambda v: ok)
        assert other != ok
        assert other == result

    def test_bind_error(self, result):
        error: Result[str, str] = Error("error")
        assert result.error != error.error

        other = result.bind(lambda: error)
        assert other != error
        assert other == result

    def test_map(self, result):
        ok = "ok"
        assert result.map(lambda v: ok) == result

    def test_map_error(self, result):
        error = "error"
        assert not isinstance(result.error, type(error))

        other = result.map_error(lambda v: error)
        assert other != result
        assert other.error == error

    def test_fold(self, result):
        ok = lambda ok_: "ok"
        error = lambda err_: "error"
        assert result.fold(ok=ok, error=error) == "error"
