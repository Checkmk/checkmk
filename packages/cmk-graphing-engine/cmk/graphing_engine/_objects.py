#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import itertools
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, KW_ONLY
from typing import NewType

from ._options import ConsolidationFunction, ServiceRef


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


@dataclass(frozen=True, kw_only=True)
class RRDMetric:
    host_name: str
    service_name: str
    metric_name: MetricName
    consolidation_function: ConsolidationFunction


@dataclass(frozen=True, kw_only=True)
class Scalars:
    lower_warning: float | None = None
    lower_critical: float | None = None
    warning: float | None = None
    critical: float | None = None
    minimum: float | None = None
    maximum: float | None = None

    def __bool__(self) -> bool:
        return any(
            value is not None
            for value in (
                self.lower_warning,
                self.lower_critical,
                self.warning,
                self.critical,
                self.minimum,
                self.maximum,
            )
        )


@dataclass(frozen=True, kw_only=True)
class RRDSource:
    service: ServiceRef
    metric_name: MetricName
    scale: float


@dataclass(frozen=True, kw_only=True)
class TranslatedMetric:
    name: MetricName
    value: float | None
    bounds: Scalars
    originals: Sequence[RRDSource]


@dataclass(frozen=True)
class WarningOf:
    metric: RRDMetric


@dataclass(frozen=True)
class CriticalOf:
    metric: RRDMetric


@dataclass(frozen=True)
class LowerWarningOf:
    metric: RRDMetric


@dataclass(frozen=True)
class LowerCriticalOf:
    metric: RRDMetric


@dataclass(frozen=True)
class MinimumOf:
    metric: RRDMetric
    color: str


@dataclass(frozen=True)
class MaximumOf:
    metric: RRDMetric
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
    RRDMetric
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


def _rrd_metrics_in_quantity(quantity: Quantity) -> Iterable[RRDMetric]:
    match quantity:
        case RRDMetric():
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
            yield quantity.metric
        case Sum():
            for operand in quantity.summands:
                yield from _rrd_metrics_in_quantity(operand)
        case Product():
            for operand in quantity.factors:
                yield from _rrd_metrics_in_quantity(operand)
        case Difference():
            yield from _rrd_metrics_in_quantity(quantity.minuend)
            yield from _rrd_metrics_in_quantity(quantity.subtrahend)
        case Fraction():
            yield from _rrd_metrics_in_quantity(quantity.dividend)
            yield from _rrd_metrics_in_quantity(quantity.divisor)


def _scalars_of(
    rrd_metrics: Iterable[RRDMetric],
    translated_metrics: Mapping[MetricName, TranslatedMetric],
) -> Mapping[RRDMetric, Scalars]:
    return {
        metric: bounds
        for metric in rrd_metrics
        if (translated := translated_metrics.get(metric.metric_name))
        and (bounds := translated.bounds)
    }


@dataclass(frozen=True, kw_only=True)
class Graph:
    name: str
    title: str
    vertical_range: VerticalRange | None = None
    stack_groups: Sequence[StackGroup] = ()
    simple_lines: Sequence[Quantity] = ()

    def rrd_metrics(self) -> Sequence[RRDMetric]:
        return list(
            set(
                rrd_metric
                for quantity in itertools.chain(
                    (m for g in self.stack_groups for m in g.members),
                    self.simple_lines,
                )
                for rrd_metric in _rrd_metrics_in_quantity(quantity)
            )
        )

    def scalars(
        self,
        translated_metrics: Mapping[MetricName, TranslatedMetric],
    ) -> Mapping[RRDMetric, Scalars]:
        return _scalars_of(self.rrd_metrics(), translated_metrics)


@dataclass(frozen=True, kw_only=True)
class Bidirectional:
    name: str
    title: str
    lower: Graph
    upper: Graph

    def rrd_metrics(self) -> Sequence[RRDMetric]:
        return list(set((*self.lower.rrd_metrics(), *self.upper.rrd_metrics())))

    def scalars(
        self,
        translated_metrics: Mapping[MetricName, TranslatedMetric],
    ) -> Mapping[RRDMetric, Scalars]:
        return _scalars_of(self.rrd_metrics(), translated_metrics)
