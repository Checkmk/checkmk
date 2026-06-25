#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.graphing_engine import (
    AutoPrecision,
    Constant,
    Curve,
    CurveAttributes,
    DecimalNotation,
    Difference,
    EvaluatedCurve,
    EvaluatedGraph,
    EvaluatedLine,
    EvaluatedRule,
    EvaluatedStack,
    EvaluatedVerticalRange,
    FixedRange,
    Fraction,
    Line,
    MetricName,
    MinimalRange,
    Product,
    ResolvedGraph,
    RRDMetric,
    Rule,
    ScalarKind,
    ScalarOf,
    ServiceRef,
    Stack,
    Sum,
    TimeRange,
    TimeSeries,
    Unit,
    VerticalRangeKind,
)
from cmk.graphing_engine._evaluate import evaluate_graph
from cmk.graphing_engine._objects import EvaluationContext, Quantity, RRDMetricData


def _perf(
    metric_data: Mapping[RRDMetric, RRDMetricData],
) -> Mapping[ServiceRef, Mapping[MetricName, RRDMetricData]]:
    result: dict[ServiceRef, dict[MetricName, RRDMetricData]] = {}
    for metric, data in metric_data.items():
        service = ServiceRef(host_name=metric.host_name, service_name=metric.service_name)
        result.setdefault(service, {})[metric.metric_name] = data
    return result


_UNIT = Unit(notation=DecimalNotation(""), precision=AutoPrecision(2))
_TR = TimeRange(start=0, end=30, step=10)  # three data points


def _metric(name: str) -> RRDMetric:
    return RRDMetric(host_name="h", service_name="svc", metric_name=MetricName(name))


def _data(*, value: float | None, warning: float | None = None) -> RRDMetricData:
    return RRDMetricData(value=value, originals=[], warning=warning)


def _attrs(title: str, *, color: str = "#28a2f3") -> CurveAttributes:
    return CurveAttributes(title=title, unit=_UNIT, color=color)


def _curve(quantity: Quantity, title: str, *, color: str = "#28a2f3") -> Curve:
    return Curve(quantity=quantity, attributes=_attrs(title, color=color))


def _time_series(*values: float | None) -> TimeSeries:
    return TimeSeries(time_range=_TR, values=list(values))


def _evaluate_value(
    quantity: Quantity,
    metric_data: Mapping[RRDMetric, RRDMetricData],
) -> float | None:
    return quantity.evaluate_value(
        EvaluationContext(performance_data=_perf(metric_data), time_series={}, time_range=_TR)
    )


def _evaluate_time_series(
    quantity: Quantity,
    metric_data: Mapping[RRDMetric, RRDMetricData],
    time_series: Mapping[RRDMetric, TimeSeries],
    time_range: TimeRange,
) -> TimeSeries:
    return quantity.evaluate_time_series(
        EvaluationContext(
            performance_data=_perf(metric_data), time_series=time_series, time_range=time_range
        )
    )


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
            ScalarOf(metric=a, kind=ScalarKind.WARNING),
            {a: _data(value=1.0, warning=80.0)},
        )
        == 80.0
    )


def test_evaluate_value_of_a_scalar_reference_without_the_bound_is_none() -> None:
    a = _metric("a")
    assert (
        _evaluate_value(ScalarOf(metric=a, kind=ScalarKind.WARNING), {a: _data(value=1.0)}) is None
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


# --- evaluate_time_series ----------------------------------------------------------------------------


def test_evaluate_time_series_of_a_metric_returns_the_fetched_time_series() -> None:
    a = _metric("a")
    time_series = _time_series(1.0, 2.0, 3.0)
    assert _evaluate_time_series(a, {}, {a: time_series}, _TR) == time_series


def test_evaluate_time_series_of_a_missing_metric_is_all_none() -> None:
    assert _evaluate_time_series(_metric("a"), {}, {}, _TR) == _time_series(None, None, None)


def test_evaluate_time_series_of_a_constant() -> None:
    assert _evaluate_time_series(Constant(5.0), {}, {}, _TR) == _time_series(5.0, 5.0, 5.0)


def test_evaluate_time_series_of_a_scalar_reference_is_a_constant_line() -> None:
    a = _metric("a")
    metric_data = {a: _data(value=1.0, warning=80.0)}
    assert _evaluate_time_series(
        ScalarOf(metric=a, kind=ScalarKind.WARNING), metric_data, {}, _TR
    ) == _time_series(80.0, 80.0, 80.0)


def test_evaluate_time_series_of_a_sum_drops_none_points() -> None:
    a, b = _metric("a"), _metric("b")
    time_series = {a: _time_series(1.0, None, 3.0), b: _time_series(10.0, 20.0, None)}
    result = _evaluate_time_series(Sum(summands=[a, b]), {}, time_series, _TR)
    assert result == _time_series(11.0, 20.0, 3.0)


def test_evaluate_time_series_of_a_product_is_none_at_points_with_a_gap() -> None:
    a, b = _metric("a"), _metric("b")
    time_series = {a: _time_series(2.0, None, 4.0), b: _time_series(3.0, 5.0, None)}
    result = _evaluate_time_series(Product(factors=[a, b]), {}, time_series, _TR)
    assert result == _time_series(6.0, None, None)


def test_evaluate_time_series_of_a_difference() -> None:
    a, b = _metric("a"), _metric("b")
    time_series = {a: _time_series(10.0, None, 4.0), b: _time_series(3.0, 5.0, 1.0)}
    result = _evaluate_time_series(Difference(minuend=a, subtrahend=b), {}, time_series, _TR)
    assert result == _time_series(7.0, None, 3.0)


def test_evaluate_time_series_of_a_fraction_guards_zero_and_gaps() -> None:
    a, b = _metric("a"), _metric("b")
    time_series = {a: _time_series(10.0, 6.0, 4.0), b: _time_series(2.0, 0.0, None)}
    result = _evaluate_time_series(Fraction(dividend=a, divisor=b), {}, time_series, _TR)
    assert result == _time_series(5.0, None, None)


# --- evaluate_graph -----------------------------------------------------------------------------


def test_evaluate_graph_keeps_stacks_and_lines_with_their_direction() -> None:
    a, b = _metric("a"), _metric("b")
    graph = ResolvedGraph(
        name="g",
        title="g",
        kind="test",
        stacks=[Stack(members=[_curve(a, "a")], inverse=True)],
        lines=[Line(curve=_curve(b, "b"), inverse=False)],
    )
    time_series = {a: _time_series(1.0, 2.0, 3.0), b: _time_series(4.0, 5.0, 6.0)}
    metric_data = {a: _data(value=3.0), b: _data(value=6.0)}

    # Stacks (filled areas) and lines stay separate, each keeping its direction; curves carry
    # their definition title/unit/colour.
    assert evaluate_graph(graph, _perf(metric_data), time_series, _TR) == EvaluatedGraph(
        name="g",
        title="g",
        vertical_range=None,
        stacks=[
            EvaluatedStack(
                members=[
                    EvaluatedCurve(
                        attributes=_attrs("a"),
                        value=3.0,
                        time_series=_time_series(1.0, 2.0, 3.0),
                    )
                ],
                inverse=True,
            )
        ],
        lines=[
            EvaluatedLine(
                curve=EvaluatedCurve(
                    attributes=_attrs("b"),
                    value=6.0,
                    time_series=_time_series(4.0, 5.0, 6.0),
                ),
                inverse=False,
            )
        ],
        rules=[],
    )


def test_evaluate_graph_evaluates_the_stack_reference_baseline() -> None:
    floor, band = _metric("floor"), _metric("band")
    graph = ResolvedGraph(
        name="g",
        title="g",
        kind="test",
        stacks=[
            Stack(members=[_curve(band, "band")], inverse=False, reference=_curve(floor, "floor"))
        ],
    )
    metric_data = {floor: _data(value=1.0), band: _data(value=2.0)}
    time_series = {floor: _time_series(1.0), band: _time_series(2.0)}

    # The reference baseline is part of the graph's metrics (so it gets fetched) ...
    assert floor in graph.rrd_metrics()
    # ... and is evaluated onto EvaluatedStack.reference, separate from the drawn members.
    [stack] = evaluate_graph(graph, _perf(metric_data), time_series, _TR).stacks
    assert [member.attributes.title for member in stack.members] == ["band"]
    assert stack.reference is not None and stack.reference.attributes.title == "floor"


def test_evaluate_graph_drops_curves_of_missing_metrics() -> None:
    a = _metric("a")
    graph = ResolvedGraph(
        name="g",
        title="g",
        kind="test",
        stacks=[Stack(members=[_curve(_metric("gone"), "gone")], inverse=False)],
        lines=[Line(curve=_curve(a, "a"), inverse=False)],
    )
    # "gone" has no metric data, so its stack is dropped; only the line for "a" remains.
    result = evaluate_graph(
        graph, _perf({a: _data(value=3.0)}), {a: _time_series(1.0, 2.0, 3.0)}, _TR
    )
    assert result.stacks == []
    assert [line.curve.attributes.title for line in result.lines] == ["a"]


def test_evaluate_graph_builds_rules_from_thresholds_and_constants() -> None:
    a = _metric("a")
    graph = ResolvedGraph(
        name="g",
        title="g",
        kind="test",
        rules=[
            # A threshold rule: the title and colour are carried by the rule's curve attributes.
            Rule(
                curve=Curve(
                    quantity=ScalarOf(metric=a, kind=ScalarKind.WARNING),
                    attributes=CurveAttributes(title="Warning", unit=_UNIT, color="#ff0000"),
                ),
                inverse=False,
            ),
            # A constant is a scalar too, so it is a rule carrying its own title/colour/value.
            Rule(
                curve=Curve(
                    quantity=Constant(42.0),
                    attributes=CurveAttributes(title="c", unit=_UNIT, color="#000000"),
                ),
                inverse=False,
            ),
        ],
    )
    result = evaluate_graph(graph, _perf({a: _data(value=3.0, warning=80.0)}), {}, _TR)
    assert result.rules == [
        EvaluatedRule(
            value=80.0,
            attributes=CurveAttributes(title="Warning", unit=_UNIT, color="#ff0000"),
            inverse=False,
        ),
        EvaluatedRule(
            value=42.0,
            attributes=CurveAttributes(title="c", unit=_UNIT, color="#000000"),
            inverse=False,
        ),
    ]


def test_evaluate_graph_drops_rules_without_a_value() -> None:
    a = _metric("a")
    graph = ResolvedGraph(
        name="g",
        title="g",
        kind="test",
        rules=[
            # The metric has no warn level (value None) ...
            Rule(
                curve=Curve(
                    quantity=ScalarOf(metric=a, kind=ScalarKind.WARNING),
                    attributes=CurveAttributes(title="w", unit=_UNIT, color="#ff0000"),
                ),
                inverse=False,
            ),
            # ... and "gone" has no data at all (not present).
            Rule(
                curve=Curve(
                    quantity=ScalarOf(metric=_metric("gone"), kind=ScalarKind.WARNING),
                    attributes=CurveAttributes(title="w", unit=_UNIT, color="#ff0000"),
                ),
                inverse=False,
            ),
        ],
    )
    result = evaluate_graph(graph, _perf({a: _data(value=3.0)}), {}, _TR)
    assert result.rules == []


def test_evaluate_graph_carries_the_name() -> None:
    graph = ResolvedGraph(name="my_graph", title="My graph", kind="test")
    assert evaluate_graph(graph, {}, {}, _TR).name == "my_graph"


def test_evaluate_graph_evaluates_a_fixed_range_of_constants() -> None:
    graph = ResolvedGraph(
        name="g", title="g", kind="test", vertical_range=FixedRange(lower=0, upper=100)
    )
    assert evaluate_graph(graph, {}, {}, _TR).vertical_range == EvaluatedVerticalRange(
        kind=VerticalRangeKind.FIXED, lower=0.0, upper=100.0
    )


def test_evaluate_graph_resolves_a_minimal_range_bound_expression() -> None:
    a = _metric("a")
    # The upper bound is a metric reference, resolved against the metric data; the lower is a number.
    graph = ResolvedGraph(
        name="g", title="g", kind="test", vertical_range=MinimalRange(lower=0, upper=a)
    )
    result = evaluate_graph(graph, _perf({a: _data(value=42.0)}), {}, _TR)
    assert result.vertical_range == EvaluatedVerticalRange(
        kind=VerticalRangeKind.MINIMAL, lower=0.0, upper=42.0
    )


def test_evaluate_graph_range_bound_of_a_missing_metric_is_none() -> None:
    graph = ResolvedGraph(
        name="g",
        title="g",
        kind="test",
        vertical_range=MinimalRange(lower=0, upper=_metric("gone")),
    )
    result = evaluate_graph(graph, {}, {}, _TR)
    assert result.vertical_range == EvaluatedVerticalRange(
        kind=VerticalRangeKind.MINIMAL, lower=0.0, upper=None
    )
