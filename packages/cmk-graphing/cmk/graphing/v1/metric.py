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
    name: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)


@dataclass(frozen=True, kw_only=True)
class Metric:
    name: MetricName
    title: Localizable
    unit: str
    color: Color


@dataclass(frozen=True, kw_only=True)
class Constant:
    value: int | float
    title: Localizable
    unit: str
    color: Color


@dataclass(frozen=True)
class WarningOf:
    name: MetricName


@dataclass(frozen=True)
class CriticalOf:
    name: MetricName


@dataclass(frozen=True)
class MinimumOf:
    name: MetricName
    _: KW_ONLY
    color: Color


@dataclass(frozen=True)
class MaximumOf:
    name: MetricName
    _: KW_ONLY
    color: Color


@dataclass(frozen=True)
class Sum:
    summands: Sequence[Quantity]
    _: KW_ONLY
    title: Localizable
    color: Color

    def __post_init__(self) -> None:
        assert self.summands


@dataclass(frozen=True)
class Product:
    factors: Sequence[Quantity]
    _: KW_ONLY
    title: Localizable
    unit: str
    color: Color

    def __post_init__(self) -> None:
        assert self.factors


@dataclass(frozen=True, kw_only=True)
class Difference:
    minuend: Quantity
    subtrahend: Quantity
    title: Localizable
    color: Color


@dataclass(frozen=True, kw_only=True)
class Fraction:
    dividend: Quantity
    divisor: Quantity
    title: Localizable
    unit: str
    color: Color


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
