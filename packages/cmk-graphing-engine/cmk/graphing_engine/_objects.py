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
class RRDMetricWithCF:
    host_name: str
    service_name: str
    metric_name: MetricName
    consolidation_function: ConsolidationFunction


@dataclass(frozen=True, kw_only=True)
class RRDMetric:
    host_name: str
    service_name: str
    metric_name: MetricName


type RRDMetricRef = RRDMetricWithCF | RRDMetric


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
class StackGroup:
    members: Sequence[Quantity]


def _rrd_metrics_in_quantity(quantity: Quantity) -> Iterable[RRDMetricRef]:
    match quantity:
        case RRDMetricWithCF() | RRDMetric():
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
class RRDOriginal:
    metric_name: MetricName
    scale: float


@dataclass(frozen=True, kw_only=True)
class RRDMetricData:
    name: MetricName
    value: float | None
    scale: float
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
    translated_metrics: Mapping[MetricName, RRDMetricData],
) -> Mapping[RRDMetricRef, RRDMetricData]:
    return {
        metric: translated
        for metric in rrd_metrics
        if (translated := translated_metrics.get(metric.metric_name)) is not None
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
    stack_groups: Sequence[StackGroup] = ()
    simple_lines: Sequence[Quantity] = ()

    def rrd_metrics(self) -> Sequence[RRDMetricRef]:
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

    def metric_data(
        self,
        translated_metrics: Mapping[MetricName, RRDMetricData],
    ) -> Mapping[RRDMetricRef, RRDMetricData]:
        return _metric_data_of(self.rrd_metrics(), translated_metrics)

    def evaluated_title(self, translated_metrics: Mapping[MetricName, RRDMetricData]) -> str:
        return _evaluate_title(self.title, translated_metrics)


@dataclass(frozen=True, kw_only=True)
class Bidirectional:
    name: str
    title: str
    lower: Graph
    upper: Graph

    def rrd_metrics(self) -> Sequence[RRDMetricRef]:
        return list(set((*self.lower.rrd_metrics(), *self.upper.rrd_metrics())))

    def metric_data(
        self,
        translated_metrics: Mapping[MetricName, RRDMetricData],
    ) -> Mapping[RRDMetricRef, RRDMetricData]:
        return _metric_data_of(self.rrd_metrics(), translated_metrics)

    def evaluated_title(self, translated_metrics: Mapping[MetricName, RRDMetricData]) -> str:
        return _evaluate_title(self.title, translated_metrics)
