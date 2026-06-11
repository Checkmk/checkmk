#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import itertools
import json
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, KW_ONLY
from typing import NewType

from ._options import ConsolidationFunction


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


# Rename/scale table keyed by check command, then by the raw (perf-data) metric name. A key may be
# a literal name or a "~<regex>" pattern matched against the raw name.


@dataclass(frozen=True, kw_only=True)
class RRDOriginal:
    metric_name: MetricName
    scale: float


@dataclass(frozen=True, kw_only=True)
class RRDMetricData:
    name: MetricName
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


def _metric_data_of(
    rrd_metrics: Iterable[RRDMetricRef],
    translated_metrics: Mapping[ServiceRef, Mapping[MetricName, RRDMetricData]],
) -> Mapping[RRDMetricRef, RRDMetricData]:
    # Each metric carries its own service, so the data is looked up per service: two services that
    # expose the same metric name must not collide.
    result: dict[RRDMetricRef, RRDMetricData] = {}
    for metric in rrd_metrics:
        service = ServiceRef(host_name=metric.host_name, service_name=metric.service_name)
        if (translated := translated_metrics.get(service, {}).get(metric.metric_name)) is not None:
            result[metric] = translated
    return result


def _flatten(
    translated_metrics: Mapping[ServiceRef, Mapping[MetricName, RRDMetricData]],
) -> Mapping[MetricName, RRDMetricData]:
    return {
        name: data
        for per_service in translated_metrics.values()
        for name, data in per_service.items()
    }


# A graph title may embed expressions referencing a metric's scalar, e.g.
# 'CPU load - _EXPRESSION:{"metric": "load1", "scalar": "max"} CPU cores'.
_TITLE_EXPRESSION_PREFIX = "_EXPRESSION:"
_TITLE_EXPRESSION_PATTERN = re.compile(re.escape(_TITLE_EXPRESSION_PREFIX) + r"\{.*?\}")
_TITLE_SCALARS: Mapping[str, Callable[[RRDMetricData], float | None]] = {
    "warn": lambda metric_data: metric_data.warning,
    "crit": lambda metric_data: metric_data.critical,
    "warn_lower": lambda metric_data: metric_data.lower_warning,
    "crit_lower": lambda metric_data: metric_data.lower_critical,
    "min": lambda metric_data: metric_data.minimum,
    "max": lambda metric_data: metric_data.maximum,
}


def _evaluate_title_expression(
    raw: str,
    translated_metrics: Mapping[MetricName, RRDMetricData],
) -> float | None:
    expression = json.loads(raw[len(_TITLE_EXPRESSION_PREFIX) :])
    if (translated := translated_metrics.get(MetricName(expression["metric"]))) is None:
        return None
    if (scalar := _TITLE_SCALARS.get(expression["scalar"])) is None:
        return None
    return scalar(translated)


def metric_names_in_title(title: str) -> Iterable[MetricName]:
    for raw in _TITLE_EXPRESSION_PATTERN.findall(title):
        yield MetricName(json.loads(raw[len(_TITLE_EXPRESSION_PREFIX) :])["metric"])


def _evaluate_title(
    title: str,
    translated_metrics: Mapping[MetricName, RRDMetricData],
) -> str:
    for raw in _TITLE_EXPRESSION_PATTERN.findall(title):
        value = _evaluate_title_expression(raw, translated_metrics)
        if value is None:
            # An expression could not be resolved: fall back to the static part of the title
            # (everything before the first dash).
            return title.split("-", maxsplit=1)[0].strip()
        # Rendering as an integer is hard-coded because it is all we need for now.
        title = title.replace(raw, str(int(value)), 1)
    return title


@dataclass(frozen=True, kw_only=True)
class Graph:
    name: str
    title: str
    vertical_range: VerticalRange | None = None
    stacks: Sequence[Stack] = ()
    lines: Sequence[Line] = ()

    def drawn_metrics(self) -> Iterable[tuple[RRDMetricRef, bool]]:
        # Each drawn metric paired with the direction (inverse) of the line drawing it.
        for group in self.stacks:
            for member in group.members:
                for rrd_metric in _rrd_metrics_in_quantity(member):
                    yield rrd_metric, group.inverse
        for line in self.lines:
            for rrd_metric in _rrd_metrics_in_quantity(line.quantity):
                yield rrd_metric, line.inverse

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

    def metric_data(
        self,
        translated_metrics: Mapping[ServiceRef, Mapping[MetricName, RRDMetricData]],
    ) -> Mapping[RRDMetricRef, RRDMetricData]:
        return _metric_data_of(self.rrd_metrics(), translated_metrics)

    def evaluated_title(
        self, translated_metrics: Mapping[ServiceRef, Mapping[MetricName, RRDMetricData]]
    ) -> str:
        return _evaluate_title(self.title, _flatten(translated_metrics))


@dataclass(frozen=True, kw_only=True)
class DiscoveredGraph[Options]:
    graph: Graph
    options: Options
    # The graph's title with its expressions evaluated against the translated metrics; graph.title
    # still carries the original, unevaluated title.
    graph_title: str
    metric_data: Mapping[RRDMetricRef, RRDMetricData]
