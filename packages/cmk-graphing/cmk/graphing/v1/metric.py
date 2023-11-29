#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, KW_ONLY

from ._color import Color
from ._localize import Localizable
from ._unit import PhysicalUnit, ScientificUnit, Unit

__all__ = [
    "Metric",
    "Constant",
    "WarningOf",
    "CriticalOf",
    "MinimumOf",
    "MaximumOf",
    "Sum",
    "Product",
    "Difference",
    "Fraction",
]


@dataclass(frozen=True)
class Metric:
    name: str
    title: Localizable
    unit: Unit | PhysicalUnit | ScientificUnit
    color: Color

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)


@dataclass(frozen=True)
class Constant:
    title: Localizable
    unit: Unit | PhysicalUnit | ScientificUnit
    color: Color
    value: int | float


@dataclass(frozen=True)
class WarningOf:
    name: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)


@dataclass(frozen=True)
class CriticalOf:
    name: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)


@dataclass(frozen=True)
class MinimumOf:
    name: str
    color: Color

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)


@dataclass(frozen=True)
class MaximumOf:
    name: str
    color: Color

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)


@dataclass(frozen=True)
class Sum:
    title: Localizable
    color: Color
    summands: Sequence[
        str
        | Constant
        | WarningOf
        | CriticalOf
        | MinimumOf
        | MaximumOf
        | Sum
        | Product
        | Difference
        | Fraction
    ]

    def __post_init__(self) -> None:
        assert self.summands
        for s in self.summands:
            if isinstance(s, str) and not s:
                raise ValueError(s)


@dataclass(frozen=True)
class Product:
    title: Localizable
    unit: Unit | PhysicalUnit | ScientificUnit
    color: Color
    factors: Sequence[
        str
        | Constant
        | WarningOf
        | CriticalOf
        | MinimumOf
        | MaximumOf
        | Sum
        | Product
        | Difference
        | Fraction
    ]

    def __post_init__(self) -> None:
        assert self.factors
        for f in self.factors:
            if isinstance(f, str) and not f:
                raise ValueError(f)


@dataclass(frozen=True)
class Difference:
    title: Localizable
    color: Color
    _: KW_ONLY
    minuend: (
        str
        | Constant
        | WarningOf
        | CriticalOf
        | MinimumOf
        | MaximumOf
        | Sum
        | Product
        | Difference
        | Fraction
    )
    subtrahend: (
        str
        | Constant
        | WarningOf
        | CriticalOf
        | MinimumOf
        | MaximumOf
        | Sum
        | Product
        | Difference
        | Fraction
    )

    def __post_init__(self) -> None:
        if isinstance(self.minuend, str) and not self.minuend:
            raise ValueError(self.minuend)
        if isinstance(self.subtrahend, str) and not self.subtrahend:
            raise ValueError(self.subtrahend)


@dataclass(frozen=True)
class Fraction:
    title: Localizable
    unit: Unit | PhysicalUnit | ScientificUnit
    color: Color
    _: KW_ONLY
    dividend: (
        str
        | Constant
        | WarningOf
        | CriticalOf
        | MinimumOf
        | MaximumOf
        | Sum
        | Product
        | Difference
        | Fraction
    )
    divisor: (
        str
        | Constant
        | WarningOf
        | CriticalOf
        | MinimumOf
        | MaximumOf
        | Sum
        | Product
        | Difference
        | Fraction
    )

    def __post_init__(self) -> None:
        if isinstance(self.dividend, str) and not self.dividend:
            raise ValueError(self.dividend)
        if isinstance(self.divisor, str) and not self.divisor:
            raise ValueError(self.divisor)
