#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import itertools
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, KW_ONLY
from typing import NewType

from ._options import ConsolidationFunction, TimeRange


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


@dataclass(frozen=True, kw_only=True)
class DisplayAttributes:
    # How a metric or quantity is rendered: its title, unit and colour.
    title: str
    unit: Unit
    color: str


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


@dataclass(frozen=True, kw_only=True)
class RRDMetricWithCF:
    host_name: str
    service_name: str
    metric_name: MetricName
    consolidation_function: ConsolidationFunction


type RRDMetricRef = RRDMetric | RRDMetricWithCF


@dataclass(frozen=True)
class WarningOf:
    metric: RRDMetricRef
    color: str


@dataclass(frozen=True)
class CriticalOf:
    metric: RRDMetricRef
    color: str


@dataclass(frozen=True)
class LowerWarningOf:
    metric: RRDMetricRef
    color: str


@dataclass(frozen=True)
class LowerCriticalOf:
    metric: RRDMetricRef
    color: str


@dataclass(frozen=True)
class MinimumOf:
    metric: RRDMetricRef
    color: str


@dataclass(frozen=True)
class MaximumOf:
    metric: RRDMetricRef
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
    RRDMetricRef
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
class Stack:
    members: Sequence[Quantity]
    # An inverse group is mirrored below the x-axis (the lower half of a former bidirectional).
    inverse: bool


@dataclass(frozen=True)
class Line:
    quantity: Quantity
    # An inverse line is mirrored below the x-axis (the lower half of a former bidirectional).
    inverse: bool


def _rrd_metrics_in_quantity(quantity: Quantity) -> Iterable[RRDMetricRef]:
    match quantity:
        case RRDMetric() | RRDMetricWithCF():
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


@dataclass(frozen=True, kw_only=True)
class ServiceRef:
    host_name: str
    service_name: str


@dataclass(frozen=True, kw_only=True)
class PerformanceValue:
    metric_name: MetricName
    value: float
    warning: float | None = None
    critical: float | None = None
    lower_warning: float | None = None
    lower_critical: float | None = None
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True, kw_only=True)
class PerformanceData:
    check_command: str
    values: Sequence[PerformanceValue]


@dataclass(frozen=True, kw_only=True)
class MetricTranslation:
    name: MetricName
    scale: float = 1.0


@dataclass(frozen=True, kw_only=True)
class RRDOriginal:
    metric_name: MetricName
    scale: float


@dataclass(frozen=True, kw_only=True)
class RRDMetricData:
    value: float | None
    originals: Sequence[RRDOriginal]
    title: str
    unit: Unit
    color: str
    lower_warning: float | None = None
    lower_critical: float | None = None
    warning: float | None = None
    critical: float | None = None
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True, kw_only=True)
class TimeSeries:
    time_range: TimeRange
    values: Sequence[float | None]


@dataclass(frozen=True, kw_only=True)
class DrawnMetric:
    # A metric drawn by a graph, paired with the direction (inverse) of the line drawing it.
    metric: RRDMetricRef
    inverse: bool


@dataclass(frozen=True, kw_only=True)
class Graph:
    name: str
    title: str
    vertical_range: VerticalRange | None = None
    stacks: Sequence[Stack] = ()
    lines: Sequence[Line] = ()

    def drawn_metrics(self) -> Iterable[DrawnMetric]:
        for group in self.stacks:
            for member in group.members:
                for rrd_metric in _rrd_metrics_in_quantity(member):
                    yield DrawnMetric(metric=rrd_metric, inverse=group.inverse)
        for line in self.lines:
            for rrd_metric in _rrd_metrics_in_quantity(line.quantity):
                yield DrawnMetric(metric=rrd_metric, inverse=line.inverse)

    def rrd_metrics(self) -> Sequence[RRDMetricRef]:
        return list(
            dict.fromkeys(
                rrd_metric
                for quantity in itertools.chain(
                    (m for g in self.stacks for m in g.members),
                    (line.quantity for line in self.lines),
                )
                for rrd_metric in _rrd_metrics_in_quantity(quantity)
            )
        )


def metric_data_of(
    graph: Graph,
    translated_metrics: Mapping[ServiceRef, Mapping[MetricName, RRDMetricData]],
) -> Mapping[RRDMetricRef, RRDMetricData]:
    # Each metric carries its own service, so the data is looked up per service: two services that
    # expose the same metric name must not collide.
    result: dict[RRDMetricRef, RRDMetricData] = {}
    for metric in graph.rrd_metrics():
        service = ServiceRef(host_name=metric.host_name, service_name=metric.service_name)
        if (translated := translated_metrics.get(service, {}).get(metric.metric_name)) is not None:
            result[metric] = translated
    return result


@dataclass(frozen=True, kw_only=True)
class DiscoveredGraph[Options]:
    graph: Graph
    options: Options
    # The graph's title with its expressions evaluated against the translated metrics; graph.title
    # still carries the original, unevaluated title.
    graph_title: str
    metric_data: Mapping[RRDMetricRef, RRDMetricData]
