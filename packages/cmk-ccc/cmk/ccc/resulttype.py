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

import abc
from collections.abc import Callable, Iterable
from typing import Final, final, NoReturn, override


class Result[T, E](abc.ABC):
    """Type/interface to the Result type.

    See Also:
        https://caml.inria.fr/pub/docs/manual-ocaml/libref/Result.html

    """

    __slots__ = ()

    @abc.abstractmethod
    @override
    def __hash__(self) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    @override
    def __eq__(self, other: object) -> bool:
        raise NotImplementedError

    @override
    def __ne__(self, other: object) -> bool:
        return not self == other

    @abc.abstractmethod
    def __lt__(self, other: object) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def __gt__(self, other: object) -> bool:
        raise NotImplementedError

    def __le__(self, other: object) -> bool:
        return self < other or self == other

    def __ge__(self, other: object) -> bool:
        return self > other or self == other

    @abc.abstractmethod
    def __iter__(self) -> Iterable[T]:
        raise NotImplementedError

    @abc.abstractmethod
    def iter_error(self) -> Iterable[E]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def ok(self) -> T:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def error(self) -> E:
        raise NotImplementedError

    def value[U](self, default: U) -> U | T:
        return default if self.is_error() else self.ok

    @abc.abstractmethod
    def is_ok(self) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def is_error(self) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def as_optional(self) -> T | None:
        raise NotImplementedError

    @abc.abstractmethod
    def map[U](self, func: Callable[[T], U]) -> Result[U, E]:
        raise NotImplementedError

    @abc.abstractmethod
    def map_error[F](self, func: Callable[[E], F]) -> Result[T, F]:
        raise NotImplementedError

    @abc.abstractmethod
    def fold[U](self, *, ok: Callable[[T], U], error: Callable[[E], U]) -> U:
        raise NotImplementedError


@final
class OK[T, E](Result[T, E]):
    """A successful computation."""

    __match_args__ = ("_ok",)
    __slots__ = ["_ok"]

    def __init__(self, ok: T) -> None:
        self._ok: Final[T] = ok

    @override
    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.ok!r})"

    @override
    def __hash__(self) -> int:
        return hash(self.ok)

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Result):
            return NotImplemented
        return isinstance(other, OK) and self.ok == other.ok

    @override
    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Result):
            return NotImplemented
        return isinstance(other, Error) or bool(self.ok < other.ok)

    @override
    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Result):
            return NotImplemented
        return not isinstance(other, Error) and bool(self.ok > other.ok)

    @override
    def __iter__(self) -> Iterable[T]:
        return iter((self.ok,))

    @override
    def iter_error(self) -> Iterable[E]:
        return iter(())

    @property
    @override
    def ok(self) -> T:
        return self._ok

    @property
    @override
    def error(self) -> NoReturn:
        raise ValueError(self)

    @override
    def is_ok(self) -> bool:
        return True

    @override
    def is_error(self) -> bool:
        return False

    @override
    def as_optional(self) -> T:
        return self.ok

    @override
    def map[U](self, func: Callable[[T], U]) -> OK[U, E]:
        return OK(func(self.ok))

    @override
    def map_error[F](self, func: Callable[[E], F]) -> OK[T, F]:
        return OK(self.ok)

    @override
    def fold[U](self, *, ok: Callable[[T], U], error: Callable[[E], U]) -> U:
        return ok(self.ok)


@final
class Error[T, E](Result[T, E]):
    """A failed computation."""

    __match_args__ = ("_error",)
    __slots__ = ["_error"]

    def __init__(self, error: E) -> None:
        self._error: Final[E] = error

    @override
    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.error!r})"

    @override
    def __hash__(self) -> int:
        return hash(self.error)

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Result):
            return NotImplemented
        return isinstance(other, Error) and self.error == other.error

    @override
    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Result):
            return NotImplemented
        return not isinstance(other, OK) and bool(self.error < other.error)

    @override
    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Result):
            return NotImplemented
        return isinstance(other, OK) or bool(self.error > other.error)

    @override
    def __iter__(self) -> Iterable[T]:
        return iter(())

    @override
    def iter_error(self) -> Iterable[E]:
        return iter((self.error,))

    @property
    @override
    def ok(self) -> NoReturn:
        raise ValueError(self)

    @property
    @override
    def error(self) -> E:
        return self._error

    @override
    def is_ok(self) -> bool:
        return False

    @override
    def is_error(self) -> bool:
        return True

    @override
    def as_optional(self) -> None:
        return None

    @override
    def map[U](self, func: Callable[[T], U]) -> Error[U, E]:
        return Error(self.error)

    @override
    def map_error[F](self, func: Callable[[E], F]) -> Error[T, F]:
        return Error(func(self.error))

    @override
    def fold[U](self, *, ok: Callable[[T], U], error: Callable[[E], U]) -> U:
        return error(self.error)


# We need a free-standing function, using a method for this would make Result[T, E] invariant in E.
def bind[T, E, U](result: Result[T, E], func: Callable[[T], Result[U, E]]) -> Result[U, E]:
    return result.fold(ok=func, error=Error)


def join[T, E](result: Result[Result[T, E], E]) -> Result[T, E]:
    return bind(result, lambda v: v)
