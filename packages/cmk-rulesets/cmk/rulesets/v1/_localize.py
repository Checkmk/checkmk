#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Providing means to localize strings"""

from __future__ import annotations

import enum
from collections.abc import Callable
from typing import assert_never, Self


class _Operation(enum.Enum):
    MOD = enum.auto()
    ADD = enum.auto()


class Localizable:
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
        Examples are given for the `Localizable` class, but they apply to all subclasses.
        Instead of using `Localizable`, you should use one of the subclasses, such as
        `Title`, `Label`, `Help` or `Message`.

        This is a simple use case:

        >>> title = Localizable("Translate this title")

        Note that the returned type only supports `%` formatting and addition.

        When adding localizables, you must make sure the translations of the individual
        components are available.

        >>> help = Localizable("Translate this. ") + Localizable("Translate this separately.")

        Sometimes you might want to format individually localized strings, to ensure
        consistent translations:

        >>> help = Localizable("Please use '%s' for foo") % Localizable("params for foo")

        Be aware that this does *not* result in an instance of a `Localizable`:

        >>> "%s!" % Localizable("hi")
        "Localizable('hi')!"

    """

    def __init__(
        self,
        arg: str | Self,
        /,
        *,
        modifier: tuple[_Operation, tuple[str | Self, ...]] | None = None,
    ) -> None:
        self._arg = arg
        self._modifier = modifier

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
        return self.__class__(self, modifier=(_Operation.ADD, (other,)))

    def __mod__(self, other: str | Self | tuple[str | Self, ...]) -> Self:
        return self.__class__(
            self, modifier=(_Operation.MOD, other if isinstance(other, tuple) else (other,))
        )

    def __rmod__(self, other: Self) -> Self:
        return self.__class__(other, modifier=(_Operation.MOD, (self,)))


class Title(Localizable):  # pylint: disable=too-few-public-methods
    """Create a localizable title which shortly describes an element"""


class Label(Localizable):  # pylint: disable=too-few-public-methods
    """Create a localizable label which acts an extension of the input field with additional
    information"""


class Help(Localizable):  # pylint: disable=too-few-public-methods
    """Create a localizable help text for more detailed descriptions which can contain more complex
    formatting"""


class Message(Localizable):  # pylint: disable=too-few-public-methods
    """Create a localizable message which notifies the user during runtime, e.g. to clarify why a
    validation has failed."""
