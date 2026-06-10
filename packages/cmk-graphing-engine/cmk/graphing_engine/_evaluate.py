#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import math
from collections.abc import Callable, Mapping, Sequence
from typing import assert_never

from ._fetch import TimeSeries
from ._objects import (
    Constant,
    CriticalOf,
    Difference,
    Fraction,
    LowerCriticalOf,
    LowerWarningOf,
    MaximumOf,
    MinimumOf,
    Product,
    Quantity,
    RRDMetric,
    RRDMetricData,
    RRDMetricRef,
    RRDMetricWithCF,
    Sum,
    WarningOf,
)
from ._options import TimeRange

# The arithmetic of the four operations, shared by the scalar and the time-time_series evaluation. Each
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
    """The time time_series of a quantity, evaluating constants and operations point by point."""
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
