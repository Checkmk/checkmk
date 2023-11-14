#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, KW_ONLY
from typing import TypeAlias

from ._color import Color
from ._localize import Localizable


@dataclass(frozen=True)
class MetricName:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError(self.value)


@dataclass(frozen=True)
class Metric:
    name: MetricName
    title: Localizable
    unit: str
    color: Color


@dataclass(frozen=True)
class Constant:
    title: Localizable
    unit: str
    color: Color
    value: int | float


@dataclass(frozen=True)
class WarningOf:
    name: MetricName


@dataclass(frozen=True)
class CriticalOf:
    name: MetricName


@dataclass(frozen=True)
class MinimumOf:
    name: MetricName
    color: Color


@dataclass(frozen=True)
class MaximumOf:
    name: MetricName
    color: Color


@dataclass(frozen=True)
class Sum:
    title: Localizable
    color: Color
    summands: Sequence[Quantity]

    def __post_init__(self) -> None:
        assert self.summands


@dataclass(frozen=True)
class Product:
    title: Localizable
    unit: str
    color: Color
    factors: Sequence[Quantity]

    def __post_init__(self) -> None:
        assert self.factors


@dataclass(frozen=True)
class Difference:
    title: Localizable
    color: Color
    _: KW_ONLY
    minuend: Quantity
    subtrahend: Quantity


@dataclass(frozen=True)
class Fraction:
    title: Localizable
    unit: str
    color: Color
    _: KW_ONLY
    dividend: Quantity
    divisor: Quantity


Quantity: TypeAlias = (
    MetricName
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
