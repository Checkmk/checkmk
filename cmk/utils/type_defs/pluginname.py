#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import string
from collections.abc import Container
from typing import Final, Self

__all__ = ["ValidatedString", "SectionName", "RuleSetName"]


class ValidatedString(abc.ABC):
    """Base class for validated strings.

    A plugin name must be a non-empty string consisting only of letters A-z, digits
    and the underscore.
    """

    VALID_CHARACTERS: Final = string.ascii_letters + "_" + string.digits

    @classmethod
    @abc.abstractmethod
    def exceptions(cls) -> Container[str]:
        """List of exceptions to validation.  Empty by default."""
        return frozenset()

    @classmethod
    def _validate_args(cls, /, __str: str) -> str:
        if __str in cls.exceptions():
            return __str

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


class SectionName(ValidatedString):
    @classmethod
    def exceptions(cls) -> Container[str]:
        return super().exceptions()


class RuleSetName(ValidatedString):
    @classmethod
    def exceptions(cls) -> Container[str]:
        """
        allow these names

        Unfortunately, we have some WATO rules that contain dots or dashes.
        In order not to break things, we allow those
        """
        return frozenset(
            (
                "drbd.net",
                "drbd.disk",
                "drbd.stats",
                "fileinfo-groups",
                "hpux_snmp_cs.cpu",
                "j4p_performance.mem",
                "j4p_performance.threads",
                "j4p_performance.uptime",
                "j4p_performance.app_state",
                "j4p_performance.app_sess",
                "j4p_performance.serv_req",
            )
        )
