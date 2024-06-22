#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import string
from typing import Final, Self

__all__ = ["ValidatedString"]


class ValidatedString:
    """Base class for validated strings."""

    # A plug-in name must be a non-empty string consisting only
    # of letters A-z, digits and the underscore.
    VALID_CHARACTERS: Final = string.ascii_letters + "_" + string.digits

    @classmethod
    def _validate_args(cls, /, __str: str) -> str:
        if not isinstance(__str, str):
            raise TypeError(f"{cls.__name__} must initialized from str")
        if not __str:
            raise ValueError(f"{cls.__name__} initializer must not be empty")

        if invalid := "".join(c for c in __str if c not in cls.VALID_CHARACTERS):
            raise ValueError(f"Invalid characters in {__str!r} for {cls.__name__}: {invalid!r}")

        return __str

    def __getnewargs__(self) -> tuple[str]:
        return (str(self),)

    def __new__(cls, /, __str: str) -> Self:
        cls._validate_args(__str)
        return super().__new__(cls)

    def __init__(self, /, __str: str) -> None:
        self._value: Final = __str
        self._hash: Final = hash(type(self).__name__ + self._value)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._value!r})"

    def __str__(self) -> str:
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            raise TypeError(f"cannot compare {self!r} and {other!r}")
        return self._value == other._value

    def __lt__(self, other: ValidatedString) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self._value < other._value

    def __le__(self, other: ValidatedString) -> bool:
        return self < other or self == other

    def __gt__(self, other: ValidatedString) -> bool:
        return not self <= other

    def __ge__(self, other: ValidatedString) -> bool:
        return not self < other

    def __hash__(self) -> int:
        return self._hash
