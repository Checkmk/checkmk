#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, KW_ONLY

from ._color import Color
from ._localize import Localizable
from ._name import Name
from ._unit import PhysicalUnit, ScientificUnit, Unit

__all__ = [
    "Name",
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
    name: Name
    title: Localizable
    unit: Unit | PhysicalUnit | ScientificUnit
    color: Color


@dataclass(frozen=True)
class Constant:
    title: Localizable
    unit: Unit | PhysicalUnit | ScientificUnit
    color: Color
    value: int | float


@dataclass(frozen=True)
class WarningOf:
    name: Name


@dataclass(frozen=True)
class CriticalOf:
    name: Name


@dataclass(frozen=True)
class MinimumOf:
    name: Name
    color: Color


@dataclass(frozen=True)
class MaximumOf:
    name: Name
    color: Color


@dataclass(frozen=True)
class Sum:
    title: Localizable
    color: Color
    summands: Sequence[
        Name
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


@dataclass(frozen=True)
class Product:
    title: Localizable
    unit: Unit | PhysicalUnit | ScientificUnit
    color: Color
    factors: Sequence[
        Name
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


@dataclass(frozen=True)
class Difference:
    title: Localizable
    color: Color
    _: KW_ONLY
    minuend: (
        Name
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
        Name
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


@dataclass(frozen=True)
class Fraction:
    title: Localizable
    unit: Unit | PhysicalUnit | ScientificUnit
    color: Color
    _: KW_ONLY
    dividend: (
        Name
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
        Name
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
