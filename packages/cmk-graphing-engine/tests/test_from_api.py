#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import Title
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable
from cmk.graphing.v2_unstable import metrics as metrics_v2_unstable
from cmk.graphing_engine import (
    AutoPrecision,
    Constant,
    CriticalOf,
    DecimalNotation,
    Difference,
    Fraction,
    Graph,
    IECNotation,
    Line,
    LowerCriticalOf,
    LowerWarningOf,
    MaximumOf,
    MetricName,
    MinimalRange,
    MinimumOf,
    parse_graph_from_api,
    Product,
    Quantity,
    RRDMetric,
    ServiceRef,
    SINotation,
    StackGroup,
    StrictPrecision,
    Sum,
    TimeNotation,
    Unit,
    WarningOf,
)


def _id(s: str) -> str:
    return s


_SERVICE = ServiceRef(host_name="host", service_name="svc")

# Every test metric is registered as blue (#28a2f3); only the colour is consulted by parsing now,
# to colour threshold lines. _rrd() below mirrors the bare metric the parser produces for a curve.
_TITLE = Title("Metric")
_METRICS = {
    name: metrics_v1.Metric(
        name=name,
        title=_TITLE,
        unit=metrics_v1.Unit(metrics_v1.DecimalNotation("")),
        color=metrics_v1.Color.BLUE,
    )
    for name in ("a", "b", "c", "x", "y")
}


def _rrd(name: str) -> RRDMetric:
    return RRDMetric(
        host_name="host",
        service_name="svc",
        metric_name=MetricName(name),
    )


def _line(quantity: Quantity) -> Line:
    return Line(quantity=quantity, inverse=False)


def _stack(*members: Quantity) -> StackGroup:
    return StackGroup(members=list(members), inverse=False)


def test_parse_graph_from_api_collapses_compound_lines_into_single_stack_group() -> None:
    graph = graphs_v1.Graph(
        name="g",
        title=Title("Title"),
        minimal_range=graphs_v1.MinimalRange(0, 100),
        compound_lines=["a", "b"],
        simple_lines=["c", metrics_v1.WarningOf("a")],
        optional=["a"],
        conflicting=["d"],
    )
    assert parse_graph_from_api(graph, _id, _SERVICE, _METRICS) == Graph(
        name="g",
        title="Title",
        vertical_range=MinimalRange(lower=0, upper=100),
        stack_groups=[_stack(_rrd("a"), _rrd("b"))],
        simple_lines=[_line(_rrd("c")), _line(WarningOf(metric=_rrd("a"), color="#28a2f3"))],
    )


def test_parse_graph_from_api_without_compound_lines_yields_no_stack_groups() -> None:
    graph = graphs_v1.Graph(name="g", title=Title("t"), simple_lines=["a"])
    parsed = parse_graph_from_api(graph, _id, _SERVICE, _METRICS)
    assert isinstance(parsed, Graph)
    assert parsed.stack_groups == []
    assert parsed.vertical_range is None


def test_parse_graph_from_api_uses_localizer() -> None:
    graph = graphs_v1.Graph(name="g", title=Title("t"), simple_lines=["a"])
    parsed = parse_graph_from_api(graph, lambda s: f"<{s}>", _SERVICE, _METRICS)
    assert isinstance(parsed, Graph)
    assert parsed.title == "<t>"


def test_parse_graph_from_api_parses_a_metric_valued_minimal_range_bound() -> None:
    graph = graphs_v1.Graph(
        name="g",
        title=Title("t"),
        # The lower bound references a metric rather than a fixed value.
        minimal_range=graphs_v1.MinimalRange("a", 100),
        simple_lines=["a"],
    )
    parsed = parse_graph_from_api(graph, _id, _SERVICE, _METRICS)
    assert isinstance(parsed, Graph)
    assert parsed.vertical_range == MinimalRange(lower=_rrd("a"), upper=100)


def test_parse_graph_from_api_threshold_uses_fallback_color_for_undefined_metric() -> None:
    graph = graphs_v1.Graph(name="g", title=Title("t"), simple_lines=[metrics_v1.WarningOf("u")])
    parsed = parse_graph_from_api(graph, _id, _SERVICE, {})
    assert isinstance(parsed, Graph)
    assert parsed.simple_lines == [_line(WarningOf(metric=_rrd("u"), color="#8c8c8c"))]


def test_parse_graph_from_api_builds_the_rrd_metric_of_a_curve() -> None:
    # A curve parses to a bare RRDMetric carrying the service's host/service; the consolidation
    # function and display attributes are supplied later (request / data layer), not by parsing.
    graph = graphs_v1.Graph(name="g", title=Title("t"), simple_lines=["a"])
    parsed = parse_graph_from_api(
        graph,
        _id,
        ServiceRef(host_name="my-host", service_name="my-service"),
        _METRICS,
    )
    assert isinstance(parsed, Graph)
    assert parsed.simple_lines == [
        _line(
            RRDMetric(
                host_name="my-host",
                service_name="my-service",
                metric_name=MetricName("a"),
            )
        )
    ]


def test_parse_graph_from_api_maps_unit_notations_and_precisions() -> None:
    graph = graphs_v1.Graph(
        name="g",
        title=Title("t"),
        simple_lines=[
            metrics_v1.Constant(
                Title("c1"),
                metrics_v1.Unit(metrics_v1.SINotation("bytes")),
                metrics_v1.Color.BLUE,
                1,
            ),
            metrics_v1.Constant(
                Title("c2"),
                metrics_v1.Unit(metrics_v1.IECNotation("bits"), metrics_v1.StrictPrecision(3)),
                metrics_v1.Color.RED,
                2,
            ),
            metrics_v1.Constant(
                Title("c3"),
                metrics_v1.Unit(metrics_v1.TimeNotation()),
                metrics_v1.Color.GREEN,
                3,
            ),
        ],
    )
    parsed = parse_graph_from_api(graph, _id, _SERVICE, _METRICS)
    assert isinstance(parsed, Graph)
    assert parsed.simple_lines == [
        _line(
            Constant(
                title="c1",
                unit=Unit(notation=SINotation("bytes"), precision=AutoPrecision(2)),
                color="#28a2f3",
                value=1,
            )
        ),
        _line(
            Constant(
                title="c2",
                unit=Unit(notation=IECNotation("bits"), precision=StrictPrecision(3)),
                color="#ed3b3b",
                value=2,
            )
        ),
        _line(
            Constant(
                title="c3",
                unit=Unit(notation=TimeNotation(), precision=AutoPrecision(2)),
                color="#15d1a0",
                value=3,
            )
        ),
    ]


def test_parse_graph_from_api_maps_warning_critical_minimum_maximum() -> None:
    graph = graphs_v1.Graph(
        name="g",
        title=Title("t"),
        simple_lines=[
            metrics_v1.WarningOf("a"),
            metrics_v1.CriticalOf("a"),
            metrics_v1.MinimumOf("a", metrics_v1.Color.GREEN),
            metrics_v1.MaximumOf("a", metrics_v1.Color.RED),
        ],
    )
    parsed = parse_graph_from_api(graph, _id, _SERVICE, _METRICS)
    assert isinstance(parsed, Graph)
    assert parsed.simple_lines == [
        # WarningOf/CriticalOf inherit the colour of the referenced metric (#28a2f3).
        _line(WarningOf(metric=_rrd("a"), color="#28a2f3")),
        _line(CriticalOf(metric=_rrd("a"), color="#28a2f3")),
        # MinimumOf/MaximumOf keep their own colour from the API.
        _line(MinimumOf(metric=_rrd("a"), color="#15d1a0")),
        _line(MaximumOf(metric=_rrd("a"), color="#ed3b3b")),
    ]


def test_parse_graph_from_api_maps_lower_warning_and_critical() -> None:
    graph = graphs_v2_unstable.Graph(
        name="g",
        title=Title("t"),
        simple_lines=[
            metrics_v2_unstable.LowerWarningOf("a"),
            metrics_v2_unstable.LowerCriticalOf("a"),
        ],
    )
    parsed = parse_graph_from_api(graph, _id, _SERVICE, _METRICS)
    assert isinstance(parsed, Graph)
    assert parsed.simple_lines == [
        _line(LowerWarningOf(metric=_rrd("a"), color="#28a2f3")),
        _line(LowerCriticalOf(metric=_rrd("a"), color="#28a2f3")),
    ]


def test_parse_graph_from_api_maps_sum_product_difference_fraction() -> None:
    graph = graphs_v1.Graph(
        name="g",
        title=Title("t"),
        simple_lines=[
            metrics_v1.Sum(Title("s"), metrics_v1.Color.BLUE, ["a", "b"]),
            metrics_v1.Product(
                Title("p"),
                metrics_v1.Unit(metrics_v1.DecimalNotation("")),
                metrics_v1.Color.RED,
                ["x", "y"],
            ),
            metrics_v1.Difference(Title("d"), metrics_v1.Color.GREEN, minuend="a", subtrahend="b"),
            metrics_v1.Fraction(
                Title("f"),
                metrics_v1.Unit(metrics_v1.DecimalNotation("")),
                metrics_v1.Color.YELLOW,
                dividend="a",
                divisor="b",
            ),
        ],
    )
    parsed = parse_graph_from_api(graph, _id, _SERVICE, _METRICS)
    assert isinstance(parsed, Graph)
    assert parsed.simple_lines == [
        _line(Sum(title="s", color="#28a2f3", summands=[_rrd("a"), _rrd("b")])),
        _line(
            Product(
                title="p",
                unit=Unit(notation=DecimalNotation(""), precision=AutoPrecision(2)),
                color="#ed3b3b",
                factors=[_rrd("x"), _rrd("y")],
            )
        ),
        _line(
            Difference(
                title="d",
                color="#15d1a0",
                minuend=_rrd("a"),
                subtrahend=_rrd("b"),
            )
        ),
        _line(
            Fraction(
                title="f",
                unit=Unit(notation=DecimalNotation(""), precision=AutoPrecision(2)),
                color="#ffd703",
                dividend=_rrd("a"),
                divisor=_rrd("b"),
            )
        ),
    ]


def test_parse_graph_from_api_recurses_into_nested_quantities() -> None:
    nested = metrics_v1.Sum(
        Title("outer"),
        metrics_v1.Color.BLUE,
        [
            "a",
            metrics_v1.Product(
                Title("inner"),
                metrics_v1.Unit(metrics_v1.DecimalNotation("")),
                metrics_v1.Color.RED,
                ["b", "c"],
            ),
        ],
    )
    graph = graphs_v1.Graph(name="g", title=Title("t"), simple_lines=[nested])
    parsed = parse_graph_from_api(graph, _id, _SERVICE, _METRICS)
    assert isinstance(parsed, Graph)
    assert parsed.simple_lines == [
        _line(
            Sum(
                title="outer",
                color="#28a2f3",
                summands=[
                    _rrd("a"),
                    Product(
                        title="inner",
                        unit=Unit(notation=DecimalNotation(""), precision=AutoPrecision(2)),
                        color="#ed3b3b",
                        factors=[_rrd("b"), _rrd("c")],
                    ),
                ],
            )
        ),
    ]


def test_parse_graph_from_api_collapses_bidirectional_into_one_graph() -> None:
    # A bidirectional becomes a single graph: the upper half normal, the lower half inverse.
    bidir = graphs_v1.Bidirectional(
        name="b",
        title=Title("title"),
        lower=graphs_v1.Graph(name="lo", title=Title("lo"), compound_lines=["a"]),
        upper=graphs_v1.Graph(name="up", title=Title("up"), compound_lines=["b"]),
    )
    assert parse_graph_from_api(bidir, _id, _SERVICE, _METRICS) == Graph(
        name="b",
        title="title",
        stack_groups=[
            StackGroup(members=[_rrd("b")], inverse=False),
            StackGroup(members=[_rrd("a")], inverse=True),
        ],
        simple_lines=[],
    )
