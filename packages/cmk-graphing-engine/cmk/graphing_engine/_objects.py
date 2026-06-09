#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import itertools
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, KW_ONLY
from typing import NewType


@dataclass(frozen=True)
class DecimalNotation:
    symbol: str


@dataclass(frozen=True)
class SINotation:
    symbol: str


@dataclass(frozen=True)
class IECNotation:
    symbol: str


@dataclass(frozen=True)
class StandardScientificNotation:
    symbol: str


@dataclass(frozen=True)
class EngineeringScientificNotation:
    symbol: str


@dataclass(frozen=True)
class TimeNotation:
    symbol: str = "s"


type Notation = (
    DecimalNotation
    | SINotation
    | IECNotation
    | StandardScientificNotation
    | EngineeringScientificNotation
    | TimeNotation
)


@dataclass(frozen=True)
class AutoPrecision:
    digits: int


@dataclass(frozen=True)
class StrictPrecision:
    digits: int


type Precision = AutoPrecision | StrictPrecision


@dataclass(frozen=True)
class Unit:
    notation: Notation
    precision: Precision


@dataclass(frozen=True)
class Constant:
    title: str
    unit: Unit
    color: str
    value: int | float


MetricName = NewType("MetricName", str)


@dataclass(frozen=True)
class WarningOf:
    metric_name: MetricName


@dataclass(frozen=True)
class CriticalOf:
    metric_name: MetricName


@dataclass(frozen=True)
class LowerWarningOf:
    metric_name: MetricName


@dataclass(frozen=True)
class LowerCriticalOf:
    metric_name: MetricName


@dataclass(frozen=True)
class MinimumOf:
    metric_name: MetricName
    color: str


@dataclass(frozen=True)
class MaximumOf:
    metric_name: MetricName
    color: str


@dataclass(frozen=True)
class Sum:
    title: str
    color: str
    summands: Sequence[Quantity]


@dataclass(frozen=True)
class Product:
    title: str
    unit: Unit
    color: str
    factors: Sequence[Quantity]


@dataclass(frozen=True)
class Difference:
    title: str
    color: str
    _: KW_ONLY
    minuend: Quantity
    subtrahend: Quantity


@dataclass(frozen=True)
class Fraction:
    title: str
    unit: Unit
    color: str
    _: KW_ONLY
    dividend: Quantity
    divisor: Quantity


type Quantity = (
    MetricName
    | Constant
    | WarningOf
    | CriticalOf
    | LowerWarningOf
    | LowerCriticalOf
    | MinimumOf
    | MaximumOf
    | Sum
    | Product
    | Difference
    | Fraction
)


type Bound = int | float | Quantity


@dataclass(frozen=True)
class MinimalRange:
    lower: Bound
    upper: Bound


@dataclass(frozen=True)
class FixedRange:
    lower: Bound
    upper: Bound


type VerticalRange = MinimalRange | FixedRange


@dataclass(frozen=True)
class StackGroup:
    members: Sequence[Quantity]


def _metric_names_in_quantity(quantity: Quantity) -> Iterable[MetricName]:
    match quantity:
        case str():
            yield quantity
        case Constant():
            return
        case (
            WarningOf()
            | CriticalOf()
            | LowerWarningOf()
            | LowerCriticalOf()
            | MinimumOf()
            | MaximumOf()
        ):
            yield quantity.metric_name
        case Sum():
            for operand in quantity.summands:
                yield from _metric_names_in_quantity(operand)
        case Product():
            for operand in quantity.factors:
                yield from _metric_names_in_quantity(operand)
        case Difference():
            yield from _metric_names_in_quantity(quantity.minuend)
            yield from _metric_names_in_quantity(quantity.subtrahend)
        case Fraction():
            yield from _metric_names_in_quantity(quantity.dividend)
            yield from _metric_names_in_quantity(quantity.divisor)


@dataclass(frozen=True, kw_only=True)
class Graph:
    name: str
    title: str
    vertical_range: VerticalRange | None = None
    stack_groups: Sequence[StackGroup] = ()
    simple_lines: Sequence[Quantity] = ()
    optional: Sequence[MetricName] = ()
    conflicting: Sequence[MetricName] = ()

    def metric_names(self) -> Sequence[MetricName]:
        return list(
            set(
                name
                for quantity in itertools.chain(
                    (m for g in self.stack_groups for m in g.members),
                    self.simple_lines,
                )
                for name in _metric_names_in_quantity(quantity)
            )
        )


@dataclass(frozen=True, kw_only=True)
class Bidirectional:
    name: str
    title: str
    lower: Graph
    upper: Graph

    def metric_names(self) -> Sequence[MetricName]:
        return list(set((*self.lower.metric_names(), *self.upper.metric_names())))
