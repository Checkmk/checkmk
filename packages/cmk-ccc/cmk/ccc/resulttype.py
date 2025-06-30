#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""An error container adapted from OCaml.

Note:
    The conversions to sequence (`to_seq`) and list (`to_list`) are not necessary.

    Use `list(Result[T, E]) -> list[T]` to convert to list and `for v in result: ...`
    for the sequence.

See Also:
    - OCaml (implemented): https://caml.inria.fr/pub/docs/manual-ocaml/libref/Result.html
    - C++: http://www.open-std.org/jtc1/sc22/wg21/docs/papers/2017/p0323r4.html
    - Haskell: https://hackage.haskell.org/package/category-extras-0.52.0/docs/Control-Monad-Either.html
    - Rust: https://doc.rust-lang.org/std/result/enum.Result.html

"""

from __future__ import annotations

import abc
from collections.abc import Callable, Iterable
from typing import Final, Generic, NoReturn, TypeVar

__all__ = ["Result", "OK", "Error"]

T_co = TypeVar("T_co", covariant=True)
U_co = TypeVar("U_co", covariant=True)
E_co = TypeVar("E_co", covariant=True)
F_co = TypeVar("F_co", covariant=True)


class Result(Generic[T_co, E_co], abc.ABC):
    """Type/interface to the Result type.

    See Also:
        https://caml.inria.fr/pub/docs/manual-ocaml/libref/Result.html

    """

    __slots__ = ()

    @abc.abstractmethod
    def __hash__(self) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def __eq__(self, other: object) -> bool:
        raise NotImplementedError

    def __ne__(self, other: object) -> bool:
        return not self == other

    @abc.abstractmethod
    def __lt__(self, other: Result[T_co, E_co]) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def __gt__(self, other: Result[T_co, E_co]) -> bool:
        raise NotImplementedError

    def __le__(self, other: Result[T_co, E_co]) -> bool:
        return self < other or self == other

    def __ge__(self, other: Result[T_co, E_co]) -> bool:
        return self > other or self == other

    @abc.abstractmethod
    def __iter__(self) -> Iterable[T_co]:
        raise NotImplementedError

    @abc.abstractmethod
    def iter_error(self) -> Iterable[E_co]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def ok(self) -> T_co:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def error(self) -> E_co:
        raise NotImplementedError

    # FIXME: Why do we need this? "Cannot use a covariant type variable as a parameter"
    def value(self, default: T_co) -> T_co:  # type: ignore[misc]
        return default if self.is_error() else self.ok

    @abc.abstractmethod
    def is_ok(self) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def is_error(self) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def as_optional(self) -> T_co | None:
        raise NotImplementedError

    def flatten(self) -> Result[T_co, E_co]:
        return self.join()

    @abc.abstractmethod
    def bind(self, func: Callable[[T_co], Result[U_co, E_co]]) -> Result[U_co, E_co]:
        raise NotImplementedError

    @abc.abstractmethod
    def join(self) -> Result[T_co, E_co]:
        raise NotImplementedError

    @abc.abstractmethod
    def map(self, func: Callable[[T_co], U_co]) -> Result[U_co, E_co]:
        raise NotImplementedError

    @abc.abstractmethod
    def map_error(self, func: Callable[[E_co], F_co]) -> Result[T_co, F_co]:
        raise NotImplementedError

    @abc.abstractmethod
    def fold(
        self,
        *,
        ok: Callable[[T_co], U_co],
        error: Callable[[E_co], U_co],
    ) -> U_co:
        raise NotImplementedError


class OK(Result[T_co, E_co]):
    """A successful computation."""

    __match_args__ = ("_ok",)
    __slots__ = ["_ok"]

    def __init__(self, ok: T_co) -> None:
        if isinstance(ok, Error):
            raise TypeError(ok)
        self._ok: Final[T_co] = ok

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.ok!r})"

    def __hash__(self) -> int:
        return hash(self.ok)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Result):
            return NotImplemented
        return self.ok == other.ok if isinstance(other, OK) else False

    def __lt__(self, other: Result[T_co, E_co]) -> bool:
        if not isinstance(other, Result):
            return NotImplemented
        if isinstance(other, Error):
            return True
        assert isinstance(other, OK)
        return self.ok < other.ok

    def __gt__(self, other: Result[T_co, E_co]) -> bool:
        if not isinstance(other, Result):
            return NotImplemented
        if isinstance(other, Error):
            return False
        assert isinstance(other, OK)
        return self.ok > other.ok

    def __iter__(self) -> Iterable[T_co]:
        return iter((self.ok,))

    def iter_error(self) -> Iterable[E_co]:
        return iter(())

    @property
    def ok(self) -> T_co:
        return self._ok

    @property
    def error(self) -> NoReturn:
        raise ValueError(self)

    def is_ok(self) -> bool:
        return True

    def is_error(self) -> bool:
        return False

    def as_optional(self) -> T_co:
        return self.ok

    def bind(self, func: Callable[[T_co], Result[U_co, E_co]]) -> Result[U_co, E_co]:
        return func(self.join().ok)

    def join(self) -> OK[T_co, E_co]:
        return self.ok.join() if isinstance(self.ok, OK) else self

    def map(self, func: Callable[[T_co], U_co]) -> OK[U_co, E_co]:
        return OK(func(self.join().ok))

    def map_error(self, _func: Callable[[E_co], F_co]) -> OK[T_co, F_co]:
        return OK(self.join().ok)

    def fold(
        self,
        *,
        ok: Callable[[T_co], U_co],
        error: Callable[[E_co], U_co],  # noqa: ARG002
    ) -> U_co:
        return ok(self.join().ok)


class Error(Result[T_co, E_co]):
    """A failed computation."""

    __match_args__ = ("_error",)
    __slots__ = ["_error"]

    def __init__(self, error: E_co) -> None:
        if isinstance(error, OK):
            raise TypeError(error)
        self._error: Final[E_co] = error

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.error!r})"

    def __hash__(self) -> int:
        return hash(self.error)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Result):
            return NotImplemented
        return self.error == other.error if isinstance(other, Error) else False

    def __lt__(self, other: Result[T_co, E_co]) -> bool:
        if not isinstance(other, Result):
            return NotImplemented
        if isinstance(other, OK):
            return False
        assert isinstance(other, Error)
        return self._error < other._error

    def __gt__(self, other: Result[T_co, E_co]) -> bool:
        if not isinstance(other, Result):
            return NotImplemented
        if isinstance(other, OK):
            return True
        assert isinstance(other, Error)
        return self._error > other._error

    def __iter__(self) -> Iterable[T_co]:
        return iter(())

    def iter_error(self) -> Iterable[E_co]:
        return iter((self.error,))

    @property
    def ok(self) -> NoReturn:
        raise ValueError(self)

    @property
    def error(self) -> E_co:
        return self._error

    def is_ok(self) -> bool:
        return False

    def is_error(self) -> bool:
        return True

    def as_optional(self) -> None:
        return None

    def bind(
        self,
        func: Callable[[T_co], Result[U_co, E_co]],  # noqa: ARG002
    ) -> Result[U_co, E_co]:
        return Error(self.join().error)

    def join(self) -> Error[T_co, E_co]:
        return self.error.join() if isinstance(self.error, Error) else self

    def map(self, _func: Callable[[T_co], U_co]) -> Error[U_co, E_co]:
        return Error(self.join().error)

    def map_error(self, func: Callable[[E_co], F_co]) -> Error[T_co, F_co]:
        return Error(func(self.join().error))

    def fold(
        self,
        *,
        ok: Callable[[T_co], U_co],  # noqa: ARG002
        error: Callable[[E_co], U_co],
    ) -> U_co:
        return error(self.join().error)
