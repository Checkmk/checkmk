#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass


@dataclass(frozen=True)
class DecimalNotation:
    """
    A unit with decimal notation has no special format.
    """

    symbol: str


@dataclass(frozen=True)
class SINotation:
    """
    A unit with the SI notation formats a number with the following magnitudes:
    y, z, a, f, p, n, µ, m, "", k, M, G, T, P, E, Z, Y.
    """

    symbol: str


@dataclass(frozen=True)
class IECNotation:
    """
    A unit with the IEC notation formats a number with the following magnitudes:
    "", Ki, Mi, Gi, Ti, Pi, Ei, Zi, Yi.
    Positive number below one use the decimal notation.
    """

    symbol: str


@dataclass(frozen=True)
class StandardScientificNotation:
    """
    A unit with the standard scientific notation formats a number as following:
    m * 10**n, where 1 <= \\|m| < 10.
    """

    symbol: str


@dataclass(frozen=True)
class EngineeringScientificNotation:
    """
    A unit with the engineering scientific notation formats a number as following:
    m * 10**n, where 1 <= \\|m| < 1000 and n % 3 == 0.
    """

    symbol: str


@dataclass(frozen=True)
class TimeNotation:
    """
    A unit with the time notation formats a number with the following magnitudes:
    µs, ms, s, min, h, d, y.
    """

    @property
    def symbol(self) -> str:
        return "s"


@dataclass(frozen=True)
class AgeNotation:
    """
    A unit with the age notation first computes <NOW> - <NUMBER> and then formats the computed
    value with the following magnitudes:
    µs, ms, s, min, h, d, y.
    """

    @property
    def symbol(self) -> str:
        return "s"


@dataclass(frozen=True)
class AutoPrecision:
    """
    A unit with auto precision rounds the fractional part to the given digits or to the latest
    non-zero digit.
    """

    digits: int

    def __post_init__(self) -> None:
        if self.digits < 0:
            raise ValueError(self.digits)


@dataclass(frozen=True)
class StrictPrecision:
    """
    A unit with strict precision rounds the fractional part to the given digits.
    """

    digits: int

    def __post_init__(self) -> None:
        if self.digits < 0:
            raise ValueError(self.digits)


@dataclass(frozen=True)
class Unit:
    """
    Defines a unit which can be used within metrics and metric operations.

    Examples:

        >>> Unit(DecimalNotation(""), StrictPrecision(0))  # rendered as integer
        Unit(notation=DecimalNotation(symbol=''), precision=StrictPrecision(digits=0))

        >>> Unit(DecimalNotation(""), StrictPrecision(2))  # rendered as float with two digits
        Unit(notation=DecimalNotation(symbol=''), precision=StrictPrecision(digits=2))

        >>> Unit(SINotation("bytes"))  # bytes which are scaled with SI prefixes
        Unit(notation=SINotation(symbol='bytes'), precision=AutoPrecision(digits=2))

        >>> Unit(IECNotation("bits"))  # bits which are scaled with IEC prefixes
        Unit(notation=IECNotation(symbol='bits'), precision=AutoPrecision(digits=2))
    """

    notation: (
        DecimalNotation
        | SINotation
        | IECNotation
        | StandardScientificNotation
        | EngineeringScientificNotation
        | TimeNotation
        | AgeNotation
    )
    precision: AutoPrecision | StrictPrecision = AutoPrecision(2)
