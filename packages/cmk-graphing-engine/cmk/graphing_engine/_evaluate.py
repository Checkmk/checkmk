#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import assert_never

from ._objects import (
    Constant,
    CriticalOf,
    Difference,
    DisplayAttributes,
    Fraction,
    Graph,
    LowerCriticalOf,
    LowerWarningOf,
    MaximumOf,
    MetricName,
    MinimumOf,
    Product,
    Quantity,
    RRDMetric,
    RRDMetricData,
    RRDMetricRef,
    RRDMetricWithCF,
    ServiceRef,
    Sum,
    TimeSeries,
    Unit,
    WarningOf,
)
from ._options import TimeRange
from ._title import evaluate_title

# The arithmetic of the four operations, shared by the scalar and the time-series evaluation. Each
# takes one "point" (the operands' values at one instant) and combines them; None means "no value".
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


def _evaluate_value_op(
    operator: _Operator,
    operands: Sequence[Quantity],
    metric_data: Mapping[RRDMetricRef, RRDMetricData],
) -> float | None:
    # An operation needs every operand: a missing one makes the whole expression unevaluable.
    values = [evaluate_value(operand, metric_data) for operand in operands]
    if any(value is None for value in values):
        return None
    return operator(values)


def evaluate_value(
    quantity: Quantity,
    metric_data: Mapping[RRDMetricRef, RRDMetricData],
) -> float | None:
    """The current value of a quantity, or None if it cannot be evaluated."""
    match quantity:
        case RRDMetric() | RRDMetricWithCF():
            return None if (data := metric_data.get(quantity)) is None else data.value
        case Constant():
            return quantity.value
        case WarningOf():
            return None if (data := metric_data.get(quantity.metric)) is None else data.warning
        case CriticalOf():
            return None if (data := metric_data.get(quantity.metric)) is None else data.critical
        case LowerWarningOf():
            return (
                None if (data := metric_data.get(quantity.metric)) is None else data.lower_warning
            )
        case LowerCriticalOf():
            return (
                None if (data := metric_data.get(quantity.metric)) is None else data.lower_critical
            )
        case MinimumOf():
            return None if (data := metric_data.get(quantity.metric)) is None else data.minimum
        case MaximumOf():
            return None if (data := metric_data.get(quantity.metric)) is None else data.maximum
        case Sum():
            return _evaluate_value_op(_op_sum, quantity.summands, metric_data)
        case Product():
            return _evaluate_value_op(_op_product, quantity.factors, metric_data)
        case Difference():
            return _evaluate_value_op(
                _op_difference, [quantity.minuend, quantity.subtrahend], metric_data
            )
        case Fraction():
            return _evaluate_value_op(
                _op_fraction, [quantity.dividend, quantity.divisor], metric_data
            )
        case _:
            assert_never(quantity)


def _apply(operator: _Operator, point: Sequence[float | None]) -> float | None:
    if all(value is None for value in point):
        return None
    return operator(point)


def _evaluate_time_series_op(
    operator: _Operator,
    operands: Sequence[Quantity],
    time_series: Mapping[RRDMetricRef, TimeSeries],
    metric_data: Mapping[RRDMetricRef, RRDMetricData],
    time_range: TimeRange,
) -> TimeSeries:
    evaluated = [
        evaluate_time_series(operand, time_series, metric_data, time_range) for operand in operands
    ]
    return TimeSeries(
        time_range=time_range,
        values=[_apply(operator, point) for point in zip(*(ts.values for ts in evaluated))],
    )


def _num_points(time_range: TimeRange) -> int:
    if time_range.step <= 0:
        return 0
    return max(0, (time_range.end - time_range.start) // time_range.step)


def _constant_time_series(value: float | None, time_range: TimeRange) -> TimeSeries:
    return TimeSeries(time_range=time_range, values=[value] * _num_points(time_range))


def evaluate_time_series(
    quantity: Quantity,
    time_series: Mapping[RRDMetricRef, TimeSeries],
    metric_data: Mapping[RRDMetricRef, RRDMetricData],
    time_range: TimeRange,
) -> TimeSeries:
    """The time series of a quantity, evaluating constants and operations point by point."""
    match quantity:
        case RRDMetric() | RRDMetricWithCF():
            existing = time_series.get(quantity)
            return existing if existing is not None else _constant_time_series(None, time_range)
        case Constant():
            return _constant_time_series(quantity.value, time_range)
        case (
            WarningOf()
            | CriticalOf()
            | LowerWarningOf()
            | LowerCriticalOf()
            | MinimumOf()
            | MaximumOf()
        ):
            return _constant_time_series(evaluate_value(quantity, metric_data), time_range)
        case Sum():
            return _evaluate_time_series_op(
                _op_sum, quantity.summands, time_series, metric_data, time_range
            )
        case Product():
            return _evaluate_time_series_op(
                _op_product, quantity.factors, time_series, metric_data, time_range
            )
        case Difference():
            return _evaluate_time_series_op(
                _op_difference,
                [quantity.minuend, quantity.subtrahend],
                time_series,
                metric_data,
                time_range,
            )
        case Fraction():
            return _evaluate_time_series_op(
                _op_fraction,
                [quantity.dividend, quantity.divisor],
                time_series,
                metric_data,
                time_range,
            )
        case _:
            assert_never(quantity)


def _attributes(
    quantity: Quantity,
    metric_data: Mapping[RRDMetricRef, RRDMetricData],
) -> DisplayAttributes | None:
    """Title, unit and colour of a drawn quantity, or None if it cannot be resolved."""
    match quantity:
        case RRDMetric() | RRDMetricWithCF():
            return (
                None
                if (data := metric_data.get(quantity)) is None
                else DisplayAttributes(title=data.title, unit=data.unit, color=data.color)
            )
        case Constant():
            return DisplayAttributes(title=quantity.title, unit=quantity.unit, color=quantity.color)
        case Product():
            return DisplayAttributes(title=quantity.title, unit=quantity.unit, color=quantity.color)
        case Fraction():
            return DisplayAttributes(title=quantity.title, unit=quantity.unit, color=quantity.color)
        case (
            WarningOf()
            | CriticalOf()
            | LowerWarningOf()
            | LowerCriticalOf()
            | MinimumOf()
            | MaximumOf()
        ):
            # A threshold line takes the unit (and title) of the metric it refers to, its own colour.
            data = metric_data.get(quantity.metric)
            return (
                None
                if data is None
                else DisplayAttributes(title=data.title, unit=data.unit, color=quantity.color)
            )
        case Sum():
            # A sum has no unit of its own; it takes the unit of its first summand.
            first = _attributes(quantity.summands[0], metric_data) if quantity.summands else None
            return (
                None
                if first is None
                else DisplayAttributes(title=quantity.title, unit=first.unit, color=quantity.color)
            )
        case Difference():
            minuend = _attributes(quantity.minuend, metric_data)
            return (
                None
                if minuend is None
                else DisplayAttributes(
                    title=quantity.title, unit=minuend.unit, color=quantity.color
                )
            )
        case _:
            assert_never(quantity)


@dataclass(frozen=True, kw_only=True)
class EvaluatedCurve:
    title: str
    unit: Unit
    color: str
    value: float | None
    time_series: TimeSeries


@dataclass(frozen=True, kw_only=True)
class EvaluatedStack:
    # A group of curves drawn as filled areas, stacked cumulatively (was compound lines).
    members: Sequence[EvaluatedCurve]
    inverse: bool


@dataclass(frozen=True, kw_only=True)
class EvaluatedLine:
    # A single curve drawn as a line (was a simple line).
    curve: EvaluatedCurve
    inverse: bool


@dataclass(frozen=True, kw_only=True)
class EvaluatedGraph:
    title: str
    stacks: Sequence[EvaluatedStack]
    lines: Sequence[EvaluatedLine]


def _evaluate_curve(
    quantity: Quantity,
    time_series: Mapping[RRDMetricRef, TimeSeries],
    metric_data: Mapping[RRDMetricRef, RRDMetricData],
    time_range: TimeRange,
) -> EvaluatedCurve | None:
    if (attributes := _attributes(quantity, metric_data)) is None:
        return None
    return EvaluatedCurve(
        title=attributes.title,
        unit=attributes.unit,
        color=attributes.color,
        value=evaluate_value(quantity, metric_data),
        time_series=evaluate_time_series(quantity, time_series, metric_data, time_range),
    )


def evaluate_graph(
    graph: Graph,
    time_series: Mapping[RRDMetricRef, TimeSeries],
    metric_data: Mapping[RRDMetricRef, RRDMetricData],
    time_range: TimeRange,
) -> EvaluatedGraph:
    """Evaluate a graph, keeping its stacks and lines so line type and stacking are preserved.

    Curves whose display attributes cannot be resolved (e.g. a missing metric) are dropped; an
    empty stack is dropped along with them.
    """
    stacks = []
    for group in graph.stacks:
        members = [
            curve
            for member in group.members
            if (curve := _evaluate_curve(member, time_series, metric_data, time_range)) is not None
        ]
        if members:
            stacks.append(EvaluatedStack(members=members, inverse=group.inverse))
    lines = [
        EvaluatedLine(curve=curve, inverse=line.inverse)
        for line in graph.lines
        if (curve := _evaluate_curve(line.quantity, time_series, metric_data, time_range))
        is not None
    ]
    # Group the metric data per service to evaluate the title's expressions against it.
    translated_metrics: dict[ServiceRef, dict[MetricName, RRDMetricData]] = {}
    for metric, data in metric_data.items():
        service = ServiceRef(host_name=metric.host_name, service_name=metric.service_name)
        translated_metrics.setdefault(service, {})[metric.metric_name] = data
    return EvaluatedGraph(
        title=evaluate_title(graph.title, translated_metrics),
        stacks=stacks,
        lines=lines,
    )
