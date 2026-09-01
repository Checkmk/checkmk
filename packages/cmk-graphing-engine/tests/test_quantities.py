#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""What the engine's own quantities evaluate to: a value and a time series per quantity kind."""

from collections.abc import Mapping

import pytest

from cmk.graphing_engine import (
    Constant,
    Difference,
    EvaluationContext,
    Fraction,
    PerformanceData,
    Product,
    QuantityProtocol,
    RRDMetric,
    ScalarKind,
    ScalarOf,
    Sum,
    TimeRange,
    TimeSeries,
)

from ._fixtures import _data, _fetched, _metric, _time_series, _TR


def _evaluate_value(
    quantity: QuantityProtocol,
    metric_data: Mapping[RRDMetric, PerformanceData],
) -> float | None:
    evaluated = quantity.evaluate(
        EvaluationContext(fetched=_fetched(metric_data, {}), time_range=_TR)
    )
    return evaluated[0].value if evaluated else None


def _evaluate_time_series(
    quantity: QuantityProtocol,
    metric_data: Mapping[RRDMetric, PerformanceData],
    time_series: Mapping[RRDMetric, TimeSeries],
    time_range: TimeRange,
) -> TimeSeries | None:
    evaluated = quantity.evaluate(
        EvaluationContext(fetched=_fetched(metric_data, time_series), time_range=time_range)
    )
    return evaluated[0].time_series if evaluated else None


# --- evaluate_value -----------------------------------------------------------------------------


def test_evaluate_value_of_a_metric() -> None:
    a = _metric("a")
    assert _evaluate_value(a, {a: _data(value=10.0)}) == 10.0


def test_evaluate_value_of_a_missing_metric_is_none() -> None:
    assert _evaluate_value(_metric("a"), {}) is None


def test_evaluate_value_of_a_constant() -> None:
    assert _evaluate_value(Constant(5.0), {}) == 5.0


def test_evaluate_value_of_a_scalar_reference() -> None:
    a = _metric("a")
    assert (
        _evaluate_value(
            ScalarOf(metric=a, scalar_kind=ScalarKind.WARNING),
            {a: _data(value=1.0, warning=80.0)},
        )
        == 80.0
    )


@pytest.mark.parametrize(
    "scalar_kind, expected",
    [
        (ScalarKind.WARNING, 80.0),
        (ScalarKind.CRITICAL, 90.0),
        (ScalarKind.LOWER_WARNING, 20.0),
        (ScalarKind.LOWER_CRITICAL, 10.0),
        (ScalarKind.MINIMUM, 0.0),
        (ScalarKind.MAXIMUM, 100.0),
    ],
)
def test_evaluate_value_of_a_scalar_reference_reads_its_own_bound(
    scalar_kind: ScalarKind, expected: float
) -> None:
    a = _metric("a")
    data = _data(
        value=1.0,
        warning=80.0,
        critical=90.0,
        lower_warning=20.0,
        lower_critical=10.0,
        minimum=0.0,
        maximum=100.0,
    )
    assert _evaluate_value(ScalarOf(metric=a, scalar_kind=scalar_kind), {a: data}) == expected


def test_evaluate_value_of_a_scalar_reference_without_the_bound_is_none() -> None:
    a = _metric("a")
    assert (
        _evaluate_value(ScalarOf(metric=a, scalar_kind=ScalarKind.WARNING), {a: _data(value=1.0)})
        is None
    )


def test_evaluate_value_of_a_sum() -> None:
    a, b = _metric("a"), _metric("b")
    metric_data = {a: _data(value=10.0), b: _data(value=2.0)}
    assert _evaluate_value(Sum(summands=[a, b]), metric_data) == 12.0


def test_evaluate_value_of_an_operation_with_a_missing_operand_is_none() -> None:
    a = _metric("a")
    metric_data = {a: _data(value=10.0)}
    assert _evaluate_value(Sum(summands=[a, _metric("b")]), metric_data) is None


def test_evaluate_value_of_a_product() -> None:
    a, b = _metric("a"), _metric("b")
    metric_data = {a: _data(value=10.0), b: _data(value=2.0)}
    assert _evaluate_value(Product(factors=[a, b]), metric_data) == 20.0


def test_evaluate_value_of_a_difference() -> None:
    a, b = _metric("a"), _metric("b")
    metric_data = {a: _data(value=10.0), b: _data(value=2.0)}
    assert _evaluate_value(Difference(minuend=a, subtrahend=b), metric_data) == 8.0


def test_evaluate_value_of_a_fraction() -> None:
    a, b = _metric("a"), _metric("b")
    metric_data = {a: _data(value=10.0), b: _data(value=2.0)}
    assert _evaluate_value(Fraction(dividend=a, divisor=b), metric_data) == 5.0


def test_evaluate_value_of_a_fraction_by_zero_is_none() -> None:
    a, b = _metric("a"), _metric("b")
    metric_data = {a: _data(value=10.0), b: _data(value=0.0)}
    assert _evaluate_value(Fraction(dividend=a, divisor=b), metric_data) is None


def test_evaluate_value_of_an_empty_sum_is_none() -> None:
    assert _evaluate_value(Sum(summands=[]), {}) is None


def test_evaluate_value_of_an_empty_product_is_none() -> None:
    # An empty product must be absent, not math.prod([]) == 1.0.
    assert _evaluate_value(Product(factors=[]), {}) is None


# --- evaluate_time_series ----------------------------------------------------------------------------


def test_evaluate_time_series_of_a_metric_returns_the_fetched_time_series() -> None:
    a = _metric("a")
    time_series = _time_series(1.0, 2.0, 3.0)
    assert _evaluate_time_series(a, {a: _data(value=1.0)}, {a: time_series}, _TR) == time_series


def test_evaluate_time_series_of_a_missing_metric_is_none() -> None:
    assert _evaluate_time_series(_metric("a"), {}, {}, _TR) is None


def test_evaluate_time_series_of_a_constant() -> None:
    assert _evaluate_time_series(Constant(5.0), {}, {}, _TR) == _time_series(5.0, 5.0, 5.0)


def test_evaluate_time_series_of_a_scalar_reference_is_a_constant_line() -> None:
    a = _metric("a")
    metric_data = {a: _data(value=1.0, warning=80.0)}
    assert _evaluate_time_series(
        ScalarOf(metric=a, scalar_kind=ScalarKind.WARNING), metric_data, {}, _TR
    ) == _time_series(80.0, 80.0, 80.0)


def test_evaluate_time_series_of_a_sum_drops_none_points() -> None:
    a, b = _metric("a"), _metric("b")
    metric_data = {a: _data(value=1.0), b: _data(value=1.0)}
    time_series = {a: _time_series(1.0, None, 3.0), b: _time_series(10.0, 20.0, None)}
    result = _evaluate_time_series(Sum(summands=[a, b]), metric_data, time_series, _TR)
    assert result == _time_series(11.0, 20.0, 3.0)


def test_evaluate_an_operation_with_an_absent_operand_is_absent() -> None:
    a = _metric("a")
    metric_data = {a: _data(value=1.0)}
    time_series = {a: _time_series(1.0, 2.0, 3.0)}
    # b is absent entirely: the sum is absent in both its value and its series, rather than the value
    # nulling while the series silently collapses to a's data.
    sum_ab = Sum(summands=[a, _metric("b")])
    assert _evaluate_value(sum_ab, metric_data) is None
    assert _evaluate_time_series(sum_ab, metric_data, time_series, _TR) is None


def test_evaluate_time_series_of_a_product_is_none_at_points_with_a_gap() -> None:
    a, b = _metric("a"), _metric("b")
    metric_data = {a: _data(value=1.0), b: _data(value=1.0)}
    time_series = {a: _time_series(2.0, None, 4.0), b: _time_series(3.0, 5.0, None)}
    result = _evaluate_time_series(Product(factors=[a, b]), metric_data, time_series, _TR)
    assert result == _time_series(6.0, None, None)


def test_evaluate_time_series_of_a_difference() -> None:
    a, b = _metric("a"), _metric("b")
    metric_data = {a: _data(value=1.0), b: _data(value=1.0)}
    time_series = {a: _time_series(10.0, None, 4.0), b: _time_series(3.0, 5.0, 1.0)}
    result = _evaluate_time_series(
        Difference(minuend=a, subtrahend=b), metric_data, time_series, _TR
    )
    assert result == _time_series(7.0, None, 3.0)


def test_evaluate_time_series_of_a_fraction_guards_zero_and_gaps() -> None:
    a, b = _metric("a"), _metric("b")
    metric_data = {a: _data(value=1.0), b: _data(value=1.0)}
    time_series = {a: _time_series(10.0, 6.0, 4.0), b: _time_series(2.0, 0.0, None)}
    result = _evaluate_time_series(Fraction(dividend=a, divisor=b), metric_data, time_series, _TR)
    assert result == _time_series(5.0, None, None)
