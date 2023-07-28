#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Providing means to localize strings"""
from __future__ import annotations

import enum
from typing import assert_never, Callable


class _Operation(enum.Enum):
    MOD = enum.auto()
    ADD = enum.auto()


class Localizable:
    """
    Create a localizable string

    The return type of this function marks its argument as "to be localized".
    The actual localization is done later by the backend. For this to work,
    the argument passed to this function needs to be present in the localization
    file.

    Args:
        string: The string to be localized.

    Returns:
        An object that can later be translated by the backend.

    Examples:

        This is a simple use case:

        >>> title = Localizable("Translate this title")

        Note that the returned type only supports `%` formatting and addition.

        When adding localizables, you must make sure the translations of the individual
        components are available.

        >>> help = Localizable("Translate this sentence. ") + Localizable("Translate this separately.")

        Sometimes you might want to format individually localized strings, to ensure
        consistent translations:

        >>> help = Localizable("Please use the ruleset '%s' for configuration") % Localizable("Parameters for the thing")

        Be aware that this does *not* result in an instance of a `Localizable`:

        >>> "%s!" % Localizable("hi")
        "Localizable('hi')!"

    """

    def __init__(
        self,
        arg: str | Localizable,
        /,
        *,
        modifier: tuple[_Operation, tuple[str | Localizable, ...]] | None = None,
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

    def __add__(self, other: Localizable) -> Localizable:
        return Localizable(self, modifier=(_Operation.ADD, (other,)))

    def __mod__(self, other: str | Localizable | tuple[str | Localizable, ...]) -> Localizable:
        return Localizable(
            self, modifier=(_Operation.MOD, other if isinstance(other, tuple) else (other,))
        )

    def __rmod__(self, other: Localizable) -> Localizable:
        return Localizable(other, modifier=(_Operation.MOD, (self,)))
