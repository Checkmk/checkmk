#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import override

from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing_engine import (
    AutoPrecision,
    Constant,
    Curve,
    CurveAttributes,
    DecimalNotation,
    EvaluatedCurve,
    EvaluatedGraph,
    EvaluatedLine,
    EvaluatedQuantity,
    EvaluatedStack,
    EvaluatedVerticalRange,
    EvaluationContext,
    FixedRange,
    Graph,
    Line,
    MetricProtocol,
    MinimalRange,
    PerformanceData,
    QuantityProtocol,
    RRDMetric,
    Rule,
    ScalarKind,
    ScalarOf,
    SeriesAttributes,
    Stack,
    Sum,
    TimeRange,
    TimeSeries,
    Unit,
    VerticalRangeKind,
)
from cmk.graphing_engine._graph_evaluate import (
    _evaluate_graph,
    _resolve_series_title,
    EvaluatedRule,
)

from ._fixtures import _data, _fetched, _metric, _time_series, _TR

_UNIT = Unit(notation=DecimalNotation(""), precision=AutoPrecision(2))


def _attrs(title: str, *, color: str = "#28a2f3") -> CurveAttributes:
    return CurveAttributes(title=title, unit=_UNIT, color=color)


def _curve(quantity: QuantityProtocol, title: str, *, color: str = "#28a2f3") -> Curve:
    return Curve(quantity=quantity, attributes=_attrs(title, color=color))


def _context(
    performance_data: Mapping[RRDMetric, PerformanceData],
    time_series: Mapping[RRDMetric, TimeSeries],
    time_range: TimeRange = _TR,
) -> EvaluationContext:
    return EvaluationContext(fetched=_fetched(performance_data, time_series), time_range=time_range)


# --- _evaluate_graph -----------------------------------------------------------------------------


def test_evaluate_graph_keeps_stacks_and_lines_with_their_direction() -> None:
    a, b = _metric("a"), _metric("b")
    graph = Graph(
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
    assert _evaluate_graph(graph, _context(metric_data, time_series)) == EvaluatedGraph(
        name="g",
        title="g",
        vertical_range=None,
        stacks=[
            EvaluatedStack(
                members=[
                    EvaluatedCurve(
                        id="-rrd_metric(h/svc/a)",
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
                    id="rrd_metric(h/svc/b)",
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
    graph = Graph(
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
    assert floor in graph.metrics()
    # ... and is evaluated onto EvaluatedStack.reference, separate from the drawn members.
    [stack] = _evaluate_graph(graph, _context(metric_data, time_series)).stacks
    assert [member.attributes.title for member in stack.members] == ["band"]
    assert stack.reference is not None and stack.reference.attributes.title == "floor"


def test_evaluate_graph_drops_curves_of_missing_metrics() -> None:
    a = _metric("a")
    graph = Graph(
        name="g",
        title="g",
        kind="test",
        stacks=[Stack(members=[_curve(_metric("gone"), "gone")], inverse=False)],
        lines=[Line(curve=_curve(a, "a"), inverse=False)],
    )
    # "gone" has no metric data, so its stack is dropped; only the line for "a" remains.
    result = _evaluate_graph(
        graph, _context({a: _data(value=3.0)}, {a: _time_series(1.0, 2.0, 3.0)})
    )
    assert result.stacks == []
    assert [line.curve.attributes.title for line in result.lines] == ["a"]


def test_evaluate_graph_builds_rules_from_thresholds_and_constants() -> None:
    a = _metric("a")
    graph = Graph(
        name="g",
        title="g",
        kind="test",
        rules=[
            # A threshold rule: the title and colour are carried by the rule's curve attributes.
            Rule(
                curve=Curve(
                    quantity=ScalarOf(metric=a, scalar_kind=ScalarKind.WARNING),
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
    result = _evaluate_graph(graph, _context({a: _data(value=3.0, warning=80.0)}, {}))
    assert result.rules == [
        EvaluatedRule(
            id="scalar_of(warning,rrd_metric(h/svc/a))",
            value=80.0,
            attributes=CurveAttributes(title="Warning", unit=_UNIT, color="#ff0000"),
            inverse=False,
        ),
        EvaluatedRule(
            id="constant(42.0)",
            value=42.0,
            attributes=CurveAttributes(title="c", unit=_UNIT, color="#000000"),
            inverse=False,
        ),
    ]


def test_evaluate_graph_drops_rules_without_a_value() -> None:
    a = _metric("a")
    graph = Graph(
        name="g",
        title="g",
        kind="test",
        rules=[
            # The metric has no warn level (value None) ...
            Rule(
                curve=Curve(
                    quantity=ScalarOf(metric=a, scalar_kind=ScalarKind.WARNING),
                    attributes=CurveAttributes(title="w", unit=_UNIT, color="#ff0000"),
                ),
                inverse=False,
            ),
            # ... and "gone" has no data at all (not present).
            Rule(
                curve=Curve(
                    quantity=ScalarOf(metric=_metric("gone"), scalar_kind=ScalarKind.WARNING),
                    attributes=CurveAttributes(title="w", unit=_UNIT, color="#ff0000"),
                ),
                inverse=False,
            ),
        ],
    )
    result = _evaluate_graph(graph, _context({a: _data(value=3.0)}, {}))
    assert result.rules == []


def test_evaluate_graph_carries_the_name() -> None:
    graph = Graph(name="my_graph", title="My graph", kind="test")
    assert _evaluate_graph(graph, _context({}, {})).name == "my_graph"


def test_evaluate_graph_evaluates_a_fixed_range_of_constants() -> None:
    graph = Graph(name="g", title="g", kind="test", vertical_range=FixedRange(lower=0, upper=100))
    assert _evaluate_graph(graph, _context({}, {})).vertical_range == EvaluatedVerticalRange(
        range_kind=VerticalRangeKind.FIXED, lower=0.0, upper=100.0
    )


def test_evaluate_graph_evaluates_a_fixed_range_with_an_open_upper_bound() -> None:
    # A half-open range (0, None): the floor is fixed at 0, the top is left to auto-scaling.
    graph = Graph(name="g", title="g", kind="test", vertical_range=FixedRange(lower=0, upper=None))
    assert _evaluate_graph(graph, _context({}, {})).vertical_range == EvaluatedVerticalRange(
        range_kind=VerticalRangeKind.FIXED, lower=0.0, upper=None
    )


def test_evaluate_graph_resolves_a_minimal_range_bound_expression() -> None:
    a = _metric("a")
    # The upper bound is a metric reference, resolved against the metric data; the lower is a number.
    graph = Graph(name="g", title="g", kind="test", vertical_range=MinimalRange(lower=0, upper=a))
    result = _evaluate_graph(graph, _context({a: _data(value=42.0)}, {}))
    assert result.vertical_range == EvaluatedVerticalRange(
        range_kind=VerticalRangeKind.MINIMAL, lower=0.0, upper=42.0
    )


def test_evaluate_graph_range_bound_of_a_missing_metric_is_none() -> None:
    graph = Graph(
        name="g",
        title="g",
        kind="test",
        vertical_range=MinimalRange(lower=0, upper=_metric("gone")),
    )
    result = _evaluate_graph(graph, _context({}, {}))
    assert result.vertical_range == EvaluatedVerticalRange(
        range_kind=VerticalRangeKind.MINIMAL, lower=0.0, upper=None
    )


# --- evaluated ids ------------------------------------------------------------------------------


def test_evaluate_graph_disambiguates_repeated_curves() -> None:
    a = _metric("a")
    graph = Graph(
        name="g",
        title="g",
        kind="test",
        lines=[
            Line(curve=_curve(a, "a"), inverse=False),
            Line(curve=_curve(a, "a"), inverse=False),
        ],
    )
    result = _evaluate_graph(
        graph, _context({a: _data(value=1.0)}, {a: _time_series(1.0, 2.0, 3.0)})
    )
    # The same metric drawn twice gets distinct ids: the base, then the base with a "#n" suffix.
    assert [line.curve.id for line in result.lines] == [
        "rrd_metric(h/svc/a)",
        "rrd_metric(h/svc/a)#2",
    ]


def test_evaluate_graph_folds_direction_into_the_id() -> None:
    a = _metric("a")
    graph = Graph(
        name="g",
        title="g",
        kind="test",
        stacks=[Stack(members=[_curve(a, "a")], inverse=True)],
        lines=[Line(curve=_curve(a, "a"), inverse=False)],
    )
    result = _evaluate_graph(
        graph, _context({a: _data(value=1.0)}, {a: _time_series(1.0, 2.0, 3.0)})
    )
    # The inverted (lower) half of a bidirectional graph and the upright half share a metric but not
    # an id: direction is folded into the base, so no "#n" disambiguation is needed.
    assert result.stacks[0].members[0].id == "-rrd_metric(h/svc/a)"
    assert result.lines[0].curve.id == "rrd_metric(h/svc/a)"


def test_evaluate_graph_rule_id_reflects_the_scalar_and_metric() -> None:
    a = _metric("a")
    graph = Graph(
        name="g",
        title="g",
        kind="test",
        rules=[
            Rule(
                curve=Curve(
                    quantity=ScalarOf(metric=a, scalar_kind=ScalarKind.WARNING),
                    attributes=_attrs("Warning"),
                ),
                inverse=False,
            )
        ],
    )
    result = _evaluate_graph(graph, _context({a: _data(value=1.0, warning=80.0)}, {}))
    assert result.rules[0].id == "scalar_of(warning,rrd_metric(h/svc/a))"


def test_evaluate_graph_preserves_ids_across_recalculation() -> None:
    a, b = _metric("a"), _metric("b")
    graph = Graph(
        name="g",
        title="g",
        kind="test",
        lines=[
            Line(curve=_curve(a, "a"), inverse=False),
            Line(curve=_curve(b, "b"), inverse=False),
        ],
    )
    first = _evaluate_graph(
        graph,
        _context(
            {a: _data(value=1.0), b: _data(value=2.0)},
            {a: _time_series(1.0, 2.0, 3.0), b: _time_series(4.0, 5.0, 6.0)},
        ),
    )
    # Re-calculate over a different range with "a" now missing (so its line is dropped): "b" keeps
    # exactly the id it had before — the id is a pure function of the graph, not of the data or range.
    other_tr = TimeRange(start=0, end=60, step=10)
    second = _evaluate_graph(
        graph,
        _context(
            {b: _data(value=9.0)},
            {b: TimeSeries(time_range=other_tr, values=[9.0] * 6)},
            other_tr,
        ),
    )
    assert [line.curve.id for line in first.lines] == ["rrd_metric(h/svc/a)", "rrd_metric(h/svc/b)"]
    assert [line.curve.id for line in second.lines] == ["rrd_metric(h/svc/b)"]


# --- source ids ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class _FannedQuantity(QuantityProtocol):
    """A fan-out leaf expanding into one curve per (label, value) pair."""

    series: Sequence[tuple[str, float]]
    series_attributes: Mapping[str, SeriesAttributes] = field(default_factory=dict)
    aggregation_kind: object | None = None

    @override
    def kind(self) -> str:
        return "fan"

    @override
    def ident(self) -> str:
        return f"{self.kind()}(test)"

    @override
    def metrics(self) -> Iterable[MetricProtocol]:
        return ()

    @override
    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        return [
            EvaluatedQuantity(
                value=value,
                time_series=_time_series(value),
                label_macros={"$SERIES_ID$": label},
                series_attributes=self.series_attributes.get(label, {}),
            )
            for label, value in self.series
        ]

    @override
    def attributes(
        self,
        _localizer: Callable[[str], str],
        _registered_metrics: Mapping[str, metrics_v1.Metric],
    ) -> CurveAttributes | None:
        return None


def test_evaluate_graph_carries_the_curve_source_id() -> None:
    a, b = _metric("a"), _metric("b")
    graph = Graph(
        name="g",
        title="g",
        kind="test",
        stacks=[
            Stack(members=[Curve(quantity=a, attributes=_attrs("a"), source_id="A")], inverse=False)
        ],
        lines=[Line(curve=_curve(b, "b"), inverse=False)],
    )
    result = _evaluate_graph(
        graph,
        _context(
            {a: _data(value=1.0), b: _data(value=2.0)},
            {a: _time_series(1.0), b: _time_series(2.0)},
        ),
    )
    assert result.stacks[0].members[0].source_id == "A"
    # An untagged curve stays untagged.
    assert result.lines[0].curve.source_id is None


def test_evaluate_graph_colours_a_fan_out_apart_even_at_a_single_series() -> None:
    alone = _FannedQuantity(series=[("only", 1.0)])
    several = _FannedQuantity(series=[("first", 1.0), ("second", 2.0)])
    [line] = _evaluate_graph(
        Graph(
            name="g", title="g", kind="test", lines=[Line(curve=_curve(alone, ""), inverse=False)]
        ),
        _context({}, {}),
    ).lines
    [first, _second] = _evaluate_graph(
        Graph(
            name="g", title="g", kind="test", lines=[Line(curve=_curve(several, ""), inverse=False)]
        ),
        _context({}, {}),
    ).lines
    assert line.curve.attributes.color != "#28a2f3"
    assert line.curve.attributes.color == first.curve.attributes.color


def test_evaluate_graph_keeps_the_curve_colour_of_a_quantity_that_never_fans_out() -> None:
    plain = _metric("a")
    [line] = _evaluate_graph(
        Graph(
            name="g", title="g", kind="test", lines=[Line(curve=_curve(plain, "a"), inverse=False)]
        ),
        _context({plain: _data(value=1.0)}, {plain: _time_series(1.0)}),
    ).lines
    assert line.curve.attributes.color == "#28a2f3"


def test_evaluate_graph_fanned_curves_share_their_source_id() -> None:
    fan = _FannedQuantity(series=[("first", 1.0), ("second", 2.0)])
    graph = Graph(
        name="g",
        title="g",
        kind="test",
        lines=[
            Line(curve=Curve(quantity=fan, attributes=_attrs("fan"), source_id="B"), inverse=False)
        ],
    )
    result = _evaluate_graph(graph, _context({}, {}))
    # Every series a source fans out into is attributable to that source, while the series ids
    # stay distinct.
    assert all(line.curve.source_id == "B" for line in result.lines)
    ids = [line.curve.id for line in result.lines]
    assert len(set(ids)) == len(ids)


# --- omitting zero curves -----------------------------------------------------------------------


def test_evaluate_graph_keeps_zero_curves_by_default() -> None:
    flat = _metric("flat")
    graph = Graph(
        name="g",
        title="g",
        kind="test",
        lines=[Line(curve=_curve(flat, "flat"), inverse=False)],
    )
    result = _evaluate_graph(
        graph, _context({flat: _data(value=0.0)}, {flat: _time_series(0.0, 0.0, 0.0)})
    )
    assert [line.curve.attributes.title for line in result.lines] == ["flat"]


def test_evaluate_graph_omits_zero_and_dataless_curves() -> None:
    flat, dataless, live = _metric("flat"), _metric("dataless"), _metric("live")
    graph = Graph(
        name="g",
        title="g",
        kind="test",
        omit_zero_curves=True,
        stacks=[Stack(members=[_curve(flat, "flat")], inverse=False)],
        lines=[
            Line(curve=_curve(dataless, "dataless"), inverse=False),
            Line(curve=_curve(live, "live"), inverse=False),
        ],
    )
    result = _evaluate_graph(
        graph,
        _context(
            {flat: _data(value=0.0), live: _data(value=4.0)},
            {
                flat: _time_series(0.0, 0.0, 0.0),
                dataless: _time_series(None, None, None),
                live: _time_series(0.0, 0.0, 4.0),
            },
        ),
    )
    # A curve flat at zero and one without a single data point are both dropped; a curve holding
    # one non-zero point stays. The stack left without members goes with them.
    assert result.stacks == []
    assert [line.curve.attributes.title for line in result.lines] == ["live"]


def test_evaluate_graph_omits_only_the_zero_series_of_a_fanned_curve() -> None:
    fan = _FannedQuantity(series=[("flat", 0.0), ("live", 2.0)])
    graph = Graph(
        name="g",
        title="g",
        kind="test",
        omit_zero_curves=True,
        lines=[Line(curve=_curve(fan, "$SERIES_ID$"), inverse=False)],
    )
    result = _evaluate_graph(graph, _context({}, {}))
    assert [line.curve.attributes.title for line in result.lines] == ["live"]


# --- per-series title macros --------------------------------------------------------------------


def test_resolve_series_title_substitutes_macros_even_for_a_single_series() -> None:
    # A macro-bearing title resolves regardless of fan-out (a query matching one service).
    assert (
        _resolve_series_title(
            "$METRIC_NAME$ - $HOST_NAME$",
            {"$METRIC_NAME$": "cpu", "$HOST_NAME$": "h0"},
            fanned=False,
        )
        == "cpu - h0"
    )


def test_resolve_series_title_appends_series_id_when_fanned_and_macro_less() -> None:
    # A macro-less title fanned into several series falls back to appending the series id.
    assert _resolve_series_title("cpu", {"$SERIES_ID$": "h0/svc"}, fanned=True) == "cpu - h0/svc"


def test_resolve_series_title_keeps_a_macro_less_title_when_not_fanned() -> None:
    assert _resolve_series_title("cpu", {"$SERIES_ID$": "h0/svc"}, fanned=False) == "cpu"


def test_resolve_series_title_skips_the_append_for_an_empty_series_id() -> None:
    assert _resolve_series_title("cpu", {"$SERIES_ID$": ""}, fanned=True) == "cpu"


def test_evaluate_graph_carries_the_macros_of_an_operation_over_one_series() -> None:
    # A fan-out leaf that matched a single series carries that series' macros, and the operation over
    # it is what gets drawn - so the macros still have to reach the curve's title.
    fan = _FannedQuantity(series=[("h0/svc", 4.0)])
    graph = Graph(
        name="g",
        title="g",
        kind="test",
        lines=[Line(curve=_curve(Sum([fan]), "$SERIES_ID$"), inverse=False)],
    )

    result = _evaluate_graph(graph, _context({}, {}))

    assert [line.curve.attributes.title for line in result.lines] == ["h0/svc"]


def test_evaluate_graph_pads_an_operation_over_operands_of_different_lengths() -> None:
    # A fetch that snapped one series differently leaves the operands on grids of different lengths.
    # The short one's missing points are gaps, not a reason to cut the whole curve short.
    long_metric, short_metric = _metric("long"), _metric("short")
    graph = Graph(
        name="g",
        title="g",
        kind="test",
        lines=[Line(curve=_curve(Sum([long_metric, short_metric]), "sum"), inverse=False)],
    )

    result = _evaluate_graph(
        graph,
        _context(
            {long_metric: _data(value=1.0), short_metric: _data(value=2.0)},
            {long_metric: _time_series(1.0, 1.0, 1.0), short_metric: _time_series(2.0)},
        ),
    )

    assert [list(line.curve.time_series.values) for line in result.lines] == [[3.0, 1.0, 1.0]]


# --- per-series attributes ----------------------------------------------------------------------


def test_evaluate_graph_carries_the_attributes_of_every_fanned_series() -> None:
    fan = _FannedQuantity(
        series=[("first", 1.0), ("second", 2.0)],
        series_attributes={
            "first": {"resource": {"host.name": "h0"}},
            "second": {"resource": {"host.name": "h1"}, "scope": {"name": "otel"}},
        },
    )
    graph = Graph(
        name="g",
        title="g",
        kind="test",
        lines=[Line(curve=_curve(fan, "fan"), inverse=False)],
    )

    result = _evaluate_graph(graph, _context({}, {}))

    assert [line.curve.series_attributes for line in result.lines] == [
        {"resource": {"host.name": "h0"}},
        {"resource": {"host.name": "h1"}, "scope": {"name": "otel"}},
    ]


def test_evaluate_graph_carries_the_attributes_of_an_operation_over_one_series() -> None:
    # The operation over a fan-out leaf is the curve that gets drawn, so the leaf's series attributes
    # have to reach it.
    fan = _FannedQuantity(
        series=[("h0/svc", 4.0)], series_attributes={"h0/svc": {"resource": {"host.name": "h0"}}}
    )
    graph = Graph(
        name="g",
        title="g",
        kind="test",
        lines=[Line(curve=_curve(Sum([fan]), "sum"), inverse=False)],
    )

    result = _evaluate_graph(graph, _context({}, {}))

    assert [line.curve.series_attributes for line in result.lines] == [
        {"resource": {"host.name": "h0"}}
    ]


def test_evaluate_graph_leaves_an_rrd_curve_without_attributes() -> None:
    metric = _metric("a")
    graph = Graph(
        name="g",
        title="g",
        kind="test",
        lines=[Line(curve=_curve(metric, "a"), inverse=False)],
    )

    result = _evaluate_graph(
        graph, _context({metric: _data(value=1.0)}, {metric: _time_series(1.0)})
    )

    assert [line.curve.series_attributes for line in result.lines] == [{}]
