#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Providing means to localize strings"""

from __future__ import annotations

import enum
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import assert_never, override, Self


class _Operation(enum.Enum):
    MOD = enum.auto()
    ADD = enum.auto()


@dataclass(frozen=True)
class _Localizable:
    """
    Base class for creating a localizable string

    This class marks its argument as "to be localized".
    The actual localization is done later by the backend. For this to work,
    the argument passed to the constructor needs to be present in the localization file.

    Args:
        arg: The string to be localized.

    Returns:
        An object that can later be translated by the backend.

    Examples:
        Examples are given for the `_Localizable` class, but they are meant to be implemented
        using the appropriate subclasses, such as :class:`Title`, :class:`Label`, :class:`Help`,
        and :class:`Message`.

        This is a simple use case:

        >>> title = _Localizable("Translate this title")

        Note that the returned type only supports `%` formatting and addition.

        When adding localizables, you must make sure the translations of the individual
        components are available.

        >>> help = _Localizable("Translate this. ") + _Localizable("Translate this separately.")

        Sometimes you might want to format individually localized strings, to ensure
        consistent translations:

        >>> help = _Localizable("Please use '%s' for foo") % _Localizable("params for foo")

        Be aware that this does *not* result in an instance of a `Localizable`:

        >>> "%s!" % _Localizable("hi")
        "_Localizable('hi')!"

    """

    _arg: str | Self
    _modifier: tuple[_Operation, tuple[str | Self, ...]] | None = field(kw_only=True, default=None)

    @override
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}({self._arg!r})"
            if self._modifier is None
            else f"{self.__class__.__name__}({self._arg!r}, {self._modifier!r})"
        )

    def localize(self, localizer: Callable[[str], str], /) -> str:
        local_arg = (
            localizer(self._arg) if isinstance(self._arg, str) else self._arg.localize(localizer)
        )
        if self._modifier is None:
            return local_arg

        operation, operands = self._modifier

        local_operands = tuple(v if isinstance(v, str) else v.localize(localizer) for v in operands)

        match operation:
            case _Operation.ADD:
                return "".join((local_arg, *local_operands))
            case _Operation.MOD:
                return local_arg % local_operands
            case _:
                assert_never(operation)

    def __add__(self, other: Self) -> Self:
        return self.__class__(self, _modifier=(_Operation.ADD, (other,)))

    def __mod__(self, other: str | Self | tuple[str | Self, ...]) -> Self:
        return self.__class__(
            self, _modifier=(_Operation.MOD, other if isinstance(other, tuple) else (other,))
        )

    def __rmod__(self, other: Self) -> Self:
        return self.__class__(other, _modifier=(_Operation.MOD, (self,)))


class Title(_Localizable):
    """Create a localizable title which shortly describes an element"""


class Label(_Localizable):
    """Create a localizable label which acts an extension of the input field with additional
    information"""


class Help(_Localizable):
    """Create a localizable help text for more detailed descriptions which can contain more complex
    formatting"""


class Message(_Localizable):
    """Create a localizable message which notifies the user during runtime, e.g. to clarify why a
    validation has failed."""
