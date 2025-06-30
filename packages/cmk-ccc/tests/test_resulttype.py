#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

import pytest

from cmk.ccc.resulttype import Error, OK, Result


class TestOk:
    @pytest.fixture
    def value(self) -> int:
        return 0

    @pytest.fixture
    def result(self, value: int) -> Result[int, object]:
        return OK(value)

    def test_bad_nesting(self, result: Result[int, object]) -> None:
        with pytest.raises(TypeError):
            Error(result)

    def test_eq(self, result: Result[int, object], value: int) -> None:
        assert (result == value) is False
        assert (value == result) is False
        assert (result != value) is True
        assert (value != result) is True

        ok: Result[int, object] = OK(value)
        assert (result == ok) is True
        assert (ok == result) is True
        assert (result != ok) is False
        assert (ok != result) is False

        err: Result[int, object] = Error(value)
        assert (result == err) is False
        assert (err == result) is False
        assert (result != err) is True
        assert (err != result) is True

    def test_ok_accessor(self, result: Result[int, object], value: int) -> None:
        assert result.ok == value

    def test_error_accessor(self, result: Result[int, object]) -> None:
        with pytest.raises(ValueError):
            _err: object = result.error

    def test_is_ok_is_true(self, result: Result[int, object]) -> None:
        assert result.is_ok() is True

    def test_is_error_is_false(self, result: Result[int, object]) -> None:
        assert result.is_error() is False

    def test_cmp_ok(self, result: Result[int, object]) -> None:
        other: Result[int, object] = OK(1)
        assert result.ok < other.ok

        assert result != other

        assert result < other
        assert result <= other
        assert result <= OK(result.ok)

        assert other > result
        assert other >= result
        assert other >= OK(other.ok)

    def test_cmp_err(self, result: Result[int, object], value: int) -> None:
        other: Result[int, object] = Error(value)
        assert result.ok == other.error

        assert result != other

        assert result < other
        assert result <= other

        assert other > result
        assert other >= result

    def test_iter(self, result: Result[int, object], value: int) -> None:
        # TODO: should not be necessary, possibly https://github.com/python/mypy/issues/12553
        assert isinstance(result, Iterable)
        assert list(result) == [value]

    def test_iter_error(self, result: Result[int, object]) -> None:
        assert not list(result.iter_error())

    def test_as_optional(self, result: Result[int, object]) -> None:
        assert result.as_optional() == result.ok

    def test_flatten1(self, result: Result[int, object]) -> None:
        nested: Result[Result[int, object], object] = OK(result)
        assert nested != result
        assert nested.flatten() == result
        assert nested.flatten() == result.flatten()
        assert nested.flatten() == nested.join()

    def test_flatten2(self, result: Result[int, object]) -> None:
        nested: Result[Result[Result[int, object], object], object] = OK(OK(result))
        assert nested != result
        assert nested.flatten() == result
        assert nested.flatten() == result.flatten()
        assert nested.flatten() == nested.join()

    def test_bind_ok(self, result: Result[int, object]) -> None:
        ok: Result[object, object] = OK("ok")
        assert result.ok != ok.ok

        other = result.bind(lambda v: ok)  # noqa: ARG005
        assert other != result
        assert other == ok

    def test_bind_error(self, result: Result[int, object], value: int) -> None:
        error: Result[int, object] = Error(value + 1)

        other = result.bind(lambda v: error)  # noqa: ARG005
        assert other != result
        assert other == error

    def test_map(self, result: Result[int, object]) -> None:
        ok = "ok"
        assert not isinstance(result.ok, type(ok))

        other = result.map(lambda v: ok)  # noqa: ARG005
        assert other != result
        assert other == OK(ok)

    def test_map_error(self, result: Result[int, object]) -> None:
        error = "error"
        assert result.map_error(lambda v: error) == result  # noqa: ARG005

    def test_fold(self, result: Result[int, object]) -> None:
        assert result.fold(ok=lambda ok_: "ok", error=lambda err_: "error") == "ok"  # noqa: ARG005


class TestError:
    @pytest.fixture
    def value(self) -> int:
        return 0

    @pytest.fixture
    def result(self, value: int) -> Result[object, int]:
        return Error(value)

    def test_bad_nesting(self, result: Result[object, int]) -> None:
        with pytest.raises(TypeError):
            OK(result)

    def test_eq(self, result: Result[object, int], value: int) -> None:
        assert (result == value) is False
        assert (value == result) is False
        assert (result != value) is True
        assert (value != result) is True

        ok: Result[object, int] = OK(value)
        assert (result == ok) is False
        assert (ok == result) is False
        assert (result != ok) is True
        assert (ok != result) is True

        err: Result[object, int] = Error(value)
        assert (result == err) is True
        assert (err == result) is True
        assert (result != err) is False
        assert (err != result) is False

    def test_ok_accessor(self, result: Result[object, int]) -> None:
        with pytest.raises(ValueError):
            _ok = result.ok

    def test_error_accessor(self, result: Result[object, int], value: int) -> None:
        assert result.error == value

    def test_is_ok_is_false(self, result: Result[object, int]) -> None:
        assert result.is_ok() is False

    def test_is_error_is_true(self, result: Result[object, int]) -> None:
        assert result.is_error() is True

    def test_cmp_err(self, result: Result[object, int]) -> None:
        other: Result[object, int] = Error(1)
        assert result.error < other.error

        assert result != other

        assert result < other
        assert result <= other
        assert result <= Error(result.error)

        assert other > result
        assert other >= result
        assert other >= Error(other.error)

    def test_cmp_ok(self, result: Result[object, int], value: int) -> None:
        other: Result[object, int] = OK(value)
        assert result.error == other.ok

        assert result != other

        assert result > other
        assert result >= other

        assert other < result
        assert other <= result

    def test_iter(self, result: Result[object, int]) -> None:
        # TODO: should not be necessary, possibly https://github.com/python/mypy/issues/12553
        assert isinstance(result, Iterable)
        assert not list(result)

    def test_iter_error(self, result: Result[object, int], value: int) -> None:
        assert list(result.iter_error()) == [value]

    def test_as_optional(self, result: Result[object, int]) -> None:
        assert result.as_optional() is None

    def test_flatten1(self, result: Result[object, int]) -> None:
        nested: Result[object, Result[object, int]] = Error(result)
        assert nested != result
        assert nested.flatten() == result
        assert nested.flatten() == result.flatten()
        assert nested.flatten() == nested.join()

    def test_flatten2(self, result: Result[object, int]) -> None:
        nested: Result[object, Result[object, Result[object, int]]] = Error(Error(result))
        assert nested != result
        assert nested.flatten() == result
        assert nested.flatten() == result.flatten()
        assert nested.flatten() == nested.join()

    def test_bind_ok(self, result: Result[object, int]) -> None:
        ok: Result[object, int] = OK("ok")

        other = result.bind(lambda v: ok)  # noqa: ARG005
        assert other != ok
        assert other == result

    def test_bind_error(self, result: Result[object, int], value: int) -> None:
        error: Result[object, int] = Error(value + 1)
        assert result.error != error.error

        other = result.bind(lambda v: error)  # noqa: ARG005
        assert other != error
        assert other == result

    def test_map(self, result: Result[object, int]) -> None:
        ok = "ok"
        assert result.map(lambda v: ok) == result  # noqa: ARG005

    def test_map_error(self, result: Result[object, int]) -> None:
        error = "error"
        assert not isinstance(result.error, type(error))

        other = result.map_error(lambda v: error)  # noqa: ARG005
        assert other != result
        assert other.error == error

    def test_fold(self, result: Result[object, int]) -> None:
        assert result.fold(ok=lambda ok_: "ok", error=lambda err_: "error") == "error"  # noqa: ARG005


def test_match_ok() -> None:
    ok: Result[int, str] = OK(1)
    match ok:
        case OK(v):
            assert v == 1
        case _:
            assert False


def test_match_error():
    err: Result[int, str] = Error("a")
    match err:
        case Error(v):
            assert v == "a"
        case _:
            assert False
