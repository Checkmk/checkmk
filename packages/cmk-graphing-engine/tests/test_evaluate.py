#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing_engine import (
    AutoPrecision,
    Constant,
    DecimalNotation,
    Difference,
    evaluate_time_series,
    evaluate_value,
    Fraction,
    MetricName,
    Product,
    RRDMetric,
    RRDMetricData,
    RRDMetricRef,
    Sum,
    TimeRange,
    TimeSeries,
    Unit,
    WarningOf,
)

_UNIT = Unit(notation=DecimalNotation(""), precision=AutoPrecision(2))
_TR = TimeRange(start=0, end=30, step=10)  # three data points


def _metric(name: str) -> RRDMetricRef:
    return RRDMetric(host_name="h", service_name="svc", metric_name=MetricName(name))


def _data(name: str, *, value: float | None, warning: float | None = None) -> RRDMetricData:
    return RRDMetricData(
        value=value,
        originals=[],
        title=name,
        unit=_UNIT,
        color="#28a2f3",
        warning=warning,
    )


def _constant(value: float) -> Constant:
    return Constant(title="c", unit=_UNIT, color="#000000", value=value)


def _time_series(*values: float | None) -> TimeSeries:
    return TimeSeries(time_range=_TR, values=list(values))


# --- evaluate_value -----------------------------------------------------------------------------


def test_evaluate_value_of_a_metric() -> None:
    a = _metric("a")
    assert evaluate_value(a, {a: _data("a", value=10.0)}) == 10.0


def test_evaluate_value_of_a_missing_metric_is_none() -> None:
    assert evaluate_value(_metric("a"), {}) is None


def test_evaluate_value_of_a_constant() -> None:
    assert evaluate_value(_constant(5.0), {}) == 5.0


def test_evaluate_value_of_a_scalar_reference() -> None:
    a = _metric("a")
    assert (
        evaluate_value(
            WarningOf(metric=a, color="#000000"), {a: _data("a", value=1.0, warning=80.0)}
        )
        == 80.0
    )


def test_evaluate_value_of_a_scalar_reference_without_the_bound_is_none() -> None:
    a = _metric("a")
    assert evaluate_value(WarningOf(metric=a, color="#000000"), {a: _data("a", value=1.0)}) is None


def test_evaluate_value_of_a_sum() -> None:
    a, b = _metric("a"), _metric("b")
    metric_data = {a: _data("a", value=10.0), b: _data("b", value=2.0)}
    assert evaluate_value(Sum(title="s", color="#000000", summands=[a, b]), metric_data) == 12.0


def test_evaluate_value_of_an_operation_with_a_missing_operand_is_none() -> None:
    a = _metric("a")
    metric_data = {a: _data("a", value=10.0)}
    assert (
        evaluate_value(Sum(title="s", color="#000000", summands=[a, _metric("b")]), metric_data)
        is None
    )


def test_evaluate_value_of_a_product() -> None:
    a, b = _metric("a"), _metric("b")
    metric_data = {a: _data("a", value=10.0), b: _data("b", value=2.0)}
    assert (
        evaluate_value(Product(title="p", unit=_UNIT, color="#000000", factors=[a, b]), metric_data)
        == 20.0
    )


def test_evaluate_value_of_a_difference() -> None:
    a, b = _metric("a"), _metric("b")
    metric_data = {a: _data("a", value=10.0), b: _data("b", value=2.0)}
    assert (
        evaluate_value(Difference(title="d", color="#000000", minuend=a, subtrahend=b), metric_data)
        == 8.0
    )


def test_evaluate_value_of_a_fraction() -> None:
    a, b = _metric("a"), _metric("b")
    metric_data = {a: _data("a", value=10.0), b: _data("b", value=2.0)}
    assert (
        evaluate_value(
            Fraction(title="f", unit=_UNIT, color="#000000", dividend=a, divisor=b), metric_data
        )
        == 5.0
    )


def test_evaluate_value_of_a_fraction_by_zero_is_none() -> None:
    a, b = _metric("a"), _metric("b")
    metric_data = {a: _data("a", value=10.0), b: _data("b", value=0.0)}
    assert (
        evaluate_value(
            Fraction(title="f", unit=_UNIT, color="#000000", dividend=a, divisor=b), metric_data
        )
        is None
    )


# --- evaluate_time_series ----------------------------------------------------------------------------


def test_evaluate_time_series_of_a_metric_returns_the_fetched_time_series() -> None:
    a = _metric("a")
    time_series = _time_series(1.0, 2.0, 3.0)
    assert evaluate_time_series(a, {a: time_series}, {}, _TR) == time_series


def test_evaluate_time_series_of_a_missing_metric_is_all_none() -> None:
    assert evaluate_time_series(_metric("a"), {}, {}, _TR) == _time_series(None, None, None)


def test_evaluate_time_series_of_a_constant() -> None:
    assert evaluate_time_series(_constant(5.0), {}, {}, _TR) == _time_series(5.0, 5.0, 5.0)


def test_evaluate_time_series_of_a_scalar_reference_is_a_constant_line() -> None:
    a = _metric("a")
    metric_data = {a: _data("a", value=1.0, warning=80.0)}
    assert evaluate_time_series(
        WarningOf(metric=a, color="#000000"), {}, metric_data, _TR
    ) == _time_series(80.0, 80.0, 80.0)


def test_evaluate_time_series_of_a_sum_drops_none_points() -> None:
    a, b = _metric("a"), _metric("b")
    time_series = {a: _time_series(1.0, None, 3.0), b: _time_series(10.0, 20.0, None)}
    result = evaluate_time_series(
        Sum(title="s", color="#000000", summands=[a, b]), time_series, {}, _TR
    )
    assert result == _time_series(11.0, 20.0, 3.0)


def test_evaluate_time_series_of_a_product_is_none_at_points_with_a_gap() -> None:
    a, b = _metric("a"), _metric("b")
    time_series = {a: _time_series(2.0, None, 4.0), b: _time_series(3.0, 5.0, None)}
    result = evaluate_time_series(
        Product(title="p", unit=_UNIT, color="#000000", factors=[a, b]), time_series, {}, _TR
    )
    assert result == _time_series(6.0, None, None)


def test_evaluate_time_series_of_a_difference() -> None:
    a, b = _metric("a"), _metric("b")
    time_series = {a: _time_series(10.0, None, 4.0), b: _time_series(3.0, 5.0, 1.0)}
    result = evaluate_time_series(
        Difference(title="d", color="#000000", minuend=a, subtrahend=b), time_series, {}, _TR
    )
    assert result == _time_series(7.0, None, 3.0)


def test_evaluate_time_series_of_a_fraction_guards_zero_and_gaps() -> None:
    a, b = _metric("a"), _metric("b")
    time_series = {a: _time_series(10.0, 6.0, 4.0), b: _time_series(2.0, 0.0, None)}
    result = evaluate_time_series(
        Fraction(title="f", unit=_UNIT, color="#000000", dividend=a, divisor=b),
        time_series,
        {},
        _TR,
    )
    assert result == _time_series(5.0, None, None)
