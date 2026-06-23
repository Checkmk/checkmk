#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import enum
import itertools
import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, KW_ONLY
from typing import NewType, Protocol

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
class CurveAttributes:
    title: str
    unit: Unit
    color: str


MetricName = NewType("MetricName", str)


@dataclass(frozen=True, kw_only=True)
class RRDMetricData:
    value: float | None
    originals: Sequence[RRDOriginal]
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
class EvaluationContext:
    metric_data: Mapping[RRDMetric, RRDMetricData]
    time_series: Mapping[RRDMetric, TimeSeries]
    time_range: TimeRange


class Quantity(Protocol):
    def rrd_metrics(self) -> Iterable[RRDMetric]: ...

    def is_present(self, context: EvaluationContext) -> bool: ...

    def evaluate_value(self, context: EvaluationContext) -> float | None: ...

    def evaluate_time_series(self, context: EvaluationContext) -> TimeSeries: ...


type _Operator = Callable[[Sequence[float | None]], float | None]


def _op_sum(point: Sequence[float | None]) -> float | None:
    return sum(value for value in point if value is not None)


def _op_product(point: Sequence[float | None]) -> float | None:
    if None in point:
        return None
    return math.prod(value for value in point if value is not None)


def _op_difference(point: Sequence[float | None]) -> float | None:
    minuend, subtrahend = point
    if minuend is None or subtrahend is None:
        return None
    return minuend - subtrahend


def _op_fraction(point: Sequence[float | None]) -> float | None:
    dividend, divisor = point
    if dividend is None or divisor is None or divisor == 0:
        return None
    return dividend / divisor


def _apply(operator: _Operator, point: Sequence[float | None]) -> float | None:
    if all(value is None for value in point):
        return None
    return operator(point)


def _num_points(time_range: TimeRange) -> int:
    if time_range.step <= 0:
        return 0
    return max(0, (time_range.end - time_range.start) // time_range.step)


def _constant_time_series(value: float | None, time_range: TimeRange) -> TimeSeries:
    return TimeSeries(time_range=time_range, values=[value] * _num_points(time_range))


def _operands_value(
    operator: _Operator,
    operands: Sequence[Quantity],
    context: EvaluationContext,
) -> float | None:
    values = [operand.evaluate_value(context) for operand in operands]
    if any(value is None for value in values):
        return None
    return operator(values)


def _operands_time_series(
    operator: _Operator,
    operands: Sequence[Quantity],
    context: EvaluationContext,
) -> TimeSeries:
    evaluated = [operand.evaluate_time_series(context) for operand in operands]
    return TimeSeries(
        time_range=context.time_range,
        values=[_apply(operator, point) for point in zip(*(ts.values for ts in evaluated))],
    )


@dataclass(frozen=True)
class Constant:
    value: int | float

    def rrd_metrics(self) -> Iterable[RRDMetric]:
        return ()

    def is_present(self, context: EvaluationContext) -> bool:  # noqa: ARG002
        return True

    def evaluate_value(self, context: EvaluationContext) -> float | None:  # noqa: ARG002
        return self.value

    def evaluate_time_series(self, context: EvaluationContext) -> TimeSeries:
        return _constant_time_series(self.value, context.time_range)


@dataclass(frozen=True, kw_only=True)
class RRDMetric:
    host_name: str
    service_name: str
    metric_name: MetricName
    # An optional per-metric consolidation function; when None the graph-wide one is used at fetch.
    consolidation_function: ConsolidationFunction | None = None

    def rrd_metrics(self) -> Iterable[RRDMetric]:
        yield self

    def is_present(self, context: EvaluationContext) -> bool:
        return self in context.metric_data

    def evaluate_value(self, context: EvaluationContext) -> float | None:
        data = context.metric_data.get(self)
        return None if data is None else data.value

    def evaluate_time_series(self, context: EvaluationContext) -> TimeSeries:
        existing = context.time_series.get(self)
        return existing if existing is not None else _constant_time_series(None, context.time_range)


class ScalarKind(enum.StrEnum):
    WARNING = "warning"
    CRITICAL = "critical"
    LOWER_WARNING = "lower_warning"
    LOWER_CRITICAL = "lower_critical"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"


_SCALAR_VALUE: Mapping[ScalarKind, Callable[[RRDMetricData], float | None]] = {
    ScalarKind.WARNING: lambda data: data.warning,
    ScalarKind.CRITICAL: lambda data: data.critical,
    ScalarKind.LOWER_WARNING: lambda data: data.lower_warning,
    ScalarKind.LOWER_CRITICAL: lambda data: data.lower_critical,
    ScalarKind.MINIMUM: lambda data: data.minimum,
    ScalarKind.MAXIMUM: lambda data: data.maximum,
}


@dataclass(frozen=True)
class ScalarOf:
    # A scalar reference of a metric (warn / crit / lower warn / lower crit / min / max bound),
    # drawn as a flat horizontal line. Unifies the former WarningOf / CriticalOf / LowerWarningOf /
    # LowerCriticalOf / MinimumOf / MaximumOf, which differed only in the data field they read.
    metric: RRDMetric
    kind: ScalarKind

    def rrd_metrics(self) -> Iterable[RRDMetric]:
        yield self.metric

    def is_present(self, context: EvaluationContext) -> bool:
        return self.metric in context.metric_data

    def evaluate_value(self, context: EvaluationContext) -> float | None:
        data = context.metric_data.get(self.metric)
        return None if data is None else _SCALAR_VALUE[self.kind](data)

    def evaluate_time_series(self, context: EvaluationContext) -> TimeSeries:
        return _constant_time_series(self.evaluate_value(context), context.time_range)


@dataclass(frozen=True)
class Sum:
    summands: Sequence[Quantity]

    def rrd_metrics(self) -> Iterable[RRDMetric]:
        for summand in self.summands:
            yield from summand.rrd_metrics()

    def is_present(self, context: EvaluationContext) -> bool:
        return bool(self.summands) and self.summands[0].is_present(context)

    def evaluate_value(self, context: EvaluationContext) -> float | None:
        return _operands_value(_op_sum, self.summands, context)

    def evaluate_time_series(self, context: EvaluationContext) -> TimeSeries:
        return _operands_time_series(_op_sum, self.summands, context)


@dataclass(frozen=True)
class Product:
    factors: Sequence[Quantity]

    def rrd_metrics(self) -> Iterable[RRDMetric]:
        for factor in self.factors:
            yield from factor.rrd_metrics()

    def is_present(self, context: EvaluationContext) -> bool:  # noqa: ARG002
        return True

    def evaluate_value(self, context: EvaluationContext) -> float | None:
        return _operands_value(_op_product, self.factors, context)

    def evaluate_time_series(self, context: EvaluationContext) -> TimeSeries:
        return _operands_time_series(_op_product, self.factors, context)


@dataclass(frozen=True)
class Difference:
    _: KW_ONLY
    minuend: Quantity
    subtrahend: Quantity

    def rrd_metrics(self) -> Iterable[RRDMetric]:
        yield from self.minuend.rrd_metrics()
        yield from self.subtrahend.rrd_metrics()

    def is_present(self, context: EvaluationContext) -> bool:
        return self.minuend.is_present(context)

    def evaluate_value(self, context: EvaluationContext) -> float | None:
        return _operands_value(_op_difference, [self.minuend, self.subtrahend], context)

    def evaluate_time_series(self, context: EvaluationContext) -> TimeSeries:
        return _operands_time_series(_op_difference, [self.minuend, self.subtrahend], context)


@dataclass(frozen=True)
class Fraction:
    _: KW_ONLY
    dividend: Quantity
    divisor: Quantity

    def rrd_metrics(self) -> Iterable[RRDMetric]:
        yield from self.dividend.rrd_metrics()
        yield from self.divisor.rrd_metrics()

    def is_present(self, context: EvaluationContext) -> bool:  # noqa: ARG002
        return True

    def evaluate_value(self, context: EvaluationContext) -> float | None:
        return _operands_value(_op_fraction, [self.dividend, self.divisor], context)

    def evaluate_time_series(self, context: EvaluationContext) -> TimeSeries:
        return _operands_time_series(_op_fraction, [self.dividend, self.divisor], context)


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


@dataclass(frozen=True, kw_only=True)
class Curve:
    quantity: Quantity
    attributes: CurveAttributes


@dataclass(frozen=True)
class Stack:
    members: Sequence[Curve]
    inverse: bool
    # An optional invisible baseline (legacy line_type="ref"): it sets the stack's floor but is not
    # drawn and not shown in the legend. The members stack on top of it.
    reference: Curve | None = None


@dataclass(frozen=True)
class Line:
    curve: Curve
    inverse: bool


@dataclass(frozen=True)
class Rule:
    curve: Curve
    inverse: bool


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
class Graph:
    name: str
    title: str
    vertical_range: VerticalRange | None = None
    stacks: Sequence[Stack] = ()
    lines: Sequence[Line] = ()
    rules: Sequence[Rule] = ()

    def rrd_metrics(self) -> Sequence[RRDMetric]:
        return list(
            dict.fromkeys(
                rrd_metric
                for quantity in itertools.chain(
                    (m.quantity for g in self.stacks for m in g.members),
                    (g.reference.quantity for g in self.stacks if g.reference is not None),
                    (line.curve.quantity for line in self.lines),
                    (rule.curve.quantity for rule in self.rules),
                )
                for rrd_metric in quantity.rrd_metrics()
            )
        )
