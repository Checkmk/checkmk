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
    Bidirectional,
    ConsolidationFunction,
    Constant,
    CriticalOf,
    DecimalNotation,
    Difference,
    Fraction,
    Graph,
    IECNotation,
    LowerCriticalOf,
    LowerWarningOf,
    MaximumOf,
    MetricName,
    MinimalRange,
    MinimumOf,
    parse_graph_from_api,
    Product,
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


_SERVICE = ServiceRef(site_id="site", host_name="host", service_name="svc")
_CF = ConsolidationFunction.AVERAGE


def _rrd(name: str) -> RRDMetric:
    return RRDMetric(
        host_name="host",
        service_name="svc",
        metric_name=MetricName(name),
        consolidation_function=_CF,
    )


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
    assert parse_graph_from_api(graph, _id, _SERVICE, _CF) == Graph(
        name="g",
        title="Title",
        vertical_range=MinimalRange(lower=0, upper=100),
        stack_groups=[StackGroup(members=[_rrd("a"), _rrd("b")])],
        simple_lines=[_rrd("c"), WarningOf(metric=_rrd("a"))],
    )


def test_parse_graph_from_api_without_compound_lines_yields_no_stack_groups() -> None:
    graph = graphs_v1.Graph(name="g", title=Title("t"), simple_lines=["a"])
    parsed = parse_graph_from_api(graph, _id, _SERVICE, _CF)
    assert isinstance(parsed, Graph)
    assert parsed.stack_groups == []
    assert parsed.vertical_range is None


def test_parse_graph_from_api_uses_localizer() -> None:
    graph = graphs_v1.Graph(name="g", title=Title("t"), simple_lines=["a"])
    parsed = parse_graph_from_api(graph, lambda s: f"<{s}>", _SERVICE, _CF)
    assert isinstance(parsed, Graph)
    assert parsed.title == "<t>"


def test_parse_graph_from_api_builds_rrd_metric_from_service_and_consolidation() -> None:
    graph = graphs_v1.Graph(name="g", title=Title("t"), simple_lines=["a"])
    parsed = parse_graph_from_api(
        graph,
        _id,
        ServiceRef(site_id="s", host_name="my-host", service_name="my-service"),
        ConsolidationFunction.MAX,
    )
    assert isinstance(parsed, Graph)
    assert parsed.simple_lines == [
        RRDMetric(
            host_name="my-host",
            service_name="my-service",
            metric_name=MetricName("a"),
            consolidation_function=ConsolidationFunction.MAX,
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
    parsed = parse_graph_from_api(graph, _id, _SERVICE, _CF)
    assert isinstance(parsed, Graph)
    assert parsed.simple_lines == [
        Constant(
            title="c1",
            unit=Unit(notation=SINotation("bytes"), precision=AutoPrecision(2)),
            color="#28a2f3",
            value=1,
        ),
        Constant(
            title="c2",
            unit=Unit(notation=IECNotation("bits"), precision=StrictPrecision(3)),
            color="#ed3b3b",
            value=2,
        ),
        Constant(
            title="c3",
            unit=Unit(notation=TimeNotation(), precision=AutoPrecision(2)),
            color="#15d1a0",
            value=3,
        ),
    ]


def test_parse_graph_from_api_maps_warning_critical_minimum_maximum() -> None:
    graph = graphs_v1.Graph(
        name="g",
        title=Title("t"),
        simple_lines=[
            metrics_v1.WarningOf("a"),
            metrics_v1.CriticalOf("a"),
            metrics_v1.MinimumOf("a", metrics_v1.Color.BLUE),
            metrics_v1.MaximumOf("a", metrics_v1.Color.RED),
        ],
    )
    parsed = parse_graph_from_api(graph, _id, _SERVICE, _CF)
    assert isinstance(parsed, Graph)
    assert parsed.simple_lines == [
        WarningOf(metric=_rrd("a")),
        CriticalOf(metric=_rrd("a")),
        MinimumOf(metric=_rrd("a"), color="#28a2f3"),
        MaximumOf(metric=_rrd("a"), color="#ed3b3b"),
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
    parsed = parse_graph_from_api(graph, _id, _SERVICE, _CF)
    assert isinstance(parsed, Graph)
    assert parsed.simple_lines == [
        LowerWarningOf(metric=_rrd("a")),
        LowerCriticalOf(metric=_rrd("a")),
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
    parsed = parse_graph_from_api(graph, _id, _SERVICE, _CF)
    assert isinstance(parsed, Graph)
    assert parsed.simple_lines == [
        Sum(title="s", color="#28a2f3", summands=[_rrd("a"), _rrd("b")]),
        Product(
            title="p",
            unit=Unit(notation=DecimalNotation(""), precision=AutoPrecision(2)),
            color="#ed3b3b",
            factors=[_rrd("x"), _rrd("y")],
        ),
        Difference(
            title="d",
            color="#15d1a0",
            minuend=_rrd("a"),
            subtrahend=_rrd("b"),
        ),
        Fraction(
            title="f",
            unit=Unit(notation=DecimalNotation(""), precision=AutoPrecision(2)),
            color="#ffd703",
            dividend=_rrd("a"),
            divisor=_rrd("b"),
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
    parsed = parse_graph_from_api(graph, _id, _SERVICE, _CF)
    assert isinstance(parsed, Graph)
    assert parsed.simple_lines == [
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
        ),
    ]


def test_parse_graph_from_api_handles_bidirectional() -> None:
    bidir = graphs_v1.Bidirectional(
        name="b",
        title=Title("title"),
        lower=graphs_v1.Graph(name="lo", title=Title("lo"), compound_lines=["a"]),
        upper=graphs_v1.Graph(name="up", title=Title("up"), compound_lines=["b"]),
    )
    assert parse_graph_from_api(bidir, _id, _SERVICE, _CF) == Bidirectional(
        name="b",
        title="title",
        lower=Graph(
            name="lo",
            title="lo",
            stack_groups=[StackGroup(members=[_rrd("a")])],
            simple_lines=[],
        ),
        upper=Graph(
            name="up",
            title="up",
            stack_groups=[StackGroup(members=[_rrd("b")])],
            simple_lines=[],
        ),
    )
