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
    ConcreteGraph,
    concretize,
    Constant,
    Curve,
    CurveAttributes,
    DecimalNotation,
    Difference,
    DiscoveredGraph,
    DiscoveredLine,
    DiscoveredRule,
    DiscoveredStack,
    Fraction,
    IECNotation,
    Line,
    MetricName,
    MinimalRange,
    Product,
    Quantity,
    RRDMetric,
    Rule,
    ScalarKind,
    ScalarOf,
    ServiceRef,
    SINotation,
    Stack,
    StrictPrecision,
    Sum,
    TimeNotation,
    Unit,
)
from cmk.graphing_engine._from_api import parse_graph_from_api


def _id(s: str) -> str:
    return s


_SERVICE = ServiceRef(host_name="host", service_name="svc")

# Every test metric is registered with title "Metric", a plain decimal unit and blue (#28a2f3).
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

_DECIMAL = Unit(notation=DecimalNotation(""), precision=AutoPrecision(2))
# The display attributes a registered test metric (or a threshold over one) resolves to.
_METRIC_ATTRS = CurveAttributes(title="Metric", unit=_DECIMAL, color="#28a2f3")
_WARN_COLOR = "#ffd000"
_CRIT_COLOR = "#ff3232"


def _rrd(name: str) -> RRDMetric:
    return RRDMetric(
        host_name="host",
        service_name="svc",
        metric_name=MetricName(name),
    )


# --- DiscoveredGraph helpers (bare quantities, no display) --------------------------------------


def _dstack(*quantities: Quantity) -> DiscoveredStack:
    return DiscoveredStack(members=list(quantities), inverse=False)


def _dline(quantity: Quantity) -> DiscoveredLine:
    return DiscoveredLine(quantity=quantity, inverse=False)


def _drule(quantity: Quantity) -> DiscoveredRule:
    return DiscoveredRule(quantity=quantity, inverse=False)


# --- ConcreteGraph helpers (curves carry resolved attributes) -----------------------------------


def _curve(quantity: Quantity, attributes: CurveAttributes = _METRIC_ATTRS) -> Curve:
    return Curve(quantity=quantity, attributes=attributes)


def _line(quantity: Quantity, attributes: CurveAttributes = _METRIC_ATTRS) -> Line:
    return Line(curve=_curve(quantity, attributes), inverse=False)


def _stack(*curves: Curve) -> Stack:
    return Stack(members=list(curves), inverse=False)


def _rule(quantity: Quantity, attributes: CurveAttributes = _METRIC_ATTRS) -> Rule:
    return Rule(curve=_curve(quantity, attributes), inverse=False)


# --- parse_graph_from_api -> DiscoveredGraph (structure, no display) -----------------------------


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
    assert parse_graph_from_api(graph, _SERVICE, _METRICS, _id) == DiscoveredGraph(
        name="g",
        title="Title",
        vertical_range=MinimalRange(lower=0, upper=100),
        stacks=[_dstack(_rrd("a"), _rrd("b"))],
        lines=[_dline(_rrd("c"))],
        # The scalar threshold becomes a horizontal rule, not a drawn line.
        rules=[_drule(ScalarOf(metric=_rrd("a"), kind=ScalarKind.WARNING))],
    )


def test_parse_graph_from_api_without_compound_lines_yields_no_stacks() -> None:
    graph = graphs_v1.Graph(name="g", title=Title("t"), simple_lines=["a"])
    parsed = parse_graph_from_api(graph, _SERVICE, _METRICS, _id)
    assert isinstance(parsed, DiscoveredGraph)
    assert parsed.stacks == []
    assert parsed.vertical_range is None


def test_parse_graph_from_api_uses_localizer() -> None:
    graph = graphs_v1.Graph(name="g", title=Title("t"), simple_lines=["a"])
    parsed = parse_graph_from_api(graph, _SERVICE, _METRICS, lambda s: f"<{s}>")
    assert parsed.title == "<t>"


def test_parse_graph_from_api_parses_a_metric_valued_minimal_range_bound() -> None:
    graph = graphs_v1.Graph(
        name="g",
        title=Title("t"),
        # The lower bound references a metric rather than a fixed value.
        minimal_range=graphs_v1.MinimalRange("a", 100),
        simple_lines=["a"],
    )
    parsed = parse_graph_from_api(graph, _SERVICE, _METRICS, _id)
    assert parsed.vertical_range == MinimalRange(lower=_rrd("a"), upper=100)


def test_parse_graph_from_api_builds_the_rrd_metric_of_a_curve() -> None:
    # A line parses to a bare RRDMetric carrying the service's host/service, with no display (that is
    # resolved later by concretize); the consolidation function is supplied later, not by parsing.
    graph = graphs_v1.Graph(name="g", title=Title("t"), simple_lines=["a"])
    parsed = parse_graph_from_api(
        graph,
        ServiceRef(host_name="my-host", service_name="my-service"),
        _METRICS,
        _id,
    )
    assert parsed.lines == [
        _dline(
            RRDMetric(
                host_name="my-host",
                service_name="my-service",
                metric_name=MetricName("a"),
            )
        )
    ]


def test_parse_graph_from_api_routes_scalars_to_rules_without_display() -> None:
    # Warn / crit scalars carry no display in the DiscoveredGraph (concretize resolves it from the
    # kind); MinimumOf / MaximumOf carry only their author-chosen colour, which is not kind-derivable.
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
    parsed = parse_graph_from_api(graph, _SERVICE, _METRICS, _id)
    assert parsed.lines == []
    assert parsed.rules == [
        _drule(ScalarOf(metric=_rrd("a"), kind=ScalarKind.WARNING)),
        _drule(ScalarOf(metric=_rrd("a"), kind=ScalarKind.CRITICAL)),
        _drule(ScalarOf(metric=_rrd("a"), kind=ScalarKind.MINIMUM, color="#15d1a0")),
        _drule(ScalarOf(metric=_rrd("a"), kind=ScalarKind.MAXIMUM, color="#ed3b3b")),
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
    parsed = parse_graph_from_api(graph, _SERVICE, _METRICS, _id)
    assert parsed.rules == [
        _drule(ScalarOf(metric=_rrd("a"), kind=ScalarKind.LOWER_WARNING)),
        _drule(ScalarOf(metric=_rrd("a"), kind=ScalarKind.LOWER_CRITICAL)),
    ]


def test_parse_graph_from_api_constants_carry_their_intrinsic_display() -> None:
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
    parsed = parse_graph_from_api(graph, _SERVICE, _METRICS, _id)
    # Constants are scalars, so they become horizontal rules; each carries its own intrinsic display.
    assert parsed.lines == []
    assert parsed.rules == [
        _drule(
            Constant(
                1,
                display=CurveAttributes(
                    title="c1",
                    unit=Unit(notation=SINotation("bytes"), precision=AutoPrecision(2)),
                    color="#28a2f3",
                ),
            )
        ),
        _drule(
            Constant(
                2,
                display=CurveAttributes(
                    title="c2",
                    unit=Unit(notation=IECNotation("bits"), precision=StrictPrecision(3)),
                    color="#ed3b3b",
                ),
            )
        ),
        _drule(
            Constant(
                3,
                display=CurveAttributes(
                    title="c3",
                    unit=Unit(notation=TimeNotation(), precision=AutoPrecision(2)),
                    color="#15d1a0",
                ),
            )
        ),
    ]


def test_parse_graph_from_api_operations_carry_their_intrinsic_display() -> None:
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
    parsed = parse_graph_from_api(graph, _SERVICE, _METRICS, _id)
    assert parsed.lines == [
        _dline(
            Sum(
                summands=[_rrd("a"), _rrd("b")],
                display=CurveAttributes(title="s", unit=_DECIMAL, color="#28a2f3"),
            )
        ),
        _dline(
            Product(
                factors=[_rrd("x"), _rrd("y")],
                display=CurveAttributes(title="p", unit=_DECIMAL, color="#ed3b3b"),
            )
        ),
        _dline(
            Difference(
                minuend=_rrd("a"),
                subtrahend=_rrd("b"),
                display=CurveAttributes(title="d", unit=_DECIMAL, color="#15d1a0"),
            )
        ),
        _dline(
            Fraction(
                dividend=_rrd("a"),
                divisor=_rrd("b"),
                display=CurveAttributes(title="f", unit=_DECIMAL, color="#ffd703"),
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
    parsed = parse_graph_from_api(graph, _SERVICE, _METRICS, _id)
    assert parsed.lines == [
        _dline(
            Sum(
                summands=[
                    _rrd("a"),
                    Product(
                        factors=[_rrd("b"), _rrd("c")],
                        display=CurveAttributes(title="inner", unit=_DECIMAL, color="#ed3b3b"),
                    ),
                ],
                display=CurveAttributes(title="outer", unit=_DECIMAL, color="#28a2f3"),
            )
        ),
    ]


def test_parse_graph_from_api_bidirectional_range_is_the_envelope_of_both_halves() -> None:
    # The combined range spans the smallest lower and largest upper across both halves, not just one.
    bidir = graphs_v1.Bidirectional(
        name="b",
        title=Title("title"),
        upper=graphs_v1.Graph(
            name="up",
            title=Title("up"),
            compound_lines=["b"],
            minimal_range=graphs_v1.MinimalRange(0, 80),
        ),
        lower=graphs_v1.Graph(
            name="lo",
            title=Title("lo"),
            compound_lines=["a"],
            minimal_range=graphs_v1.MinimalRange(10, 100),
        ),
    )
    parsed = parse_graph_from_api(bidir, _SERVICE, _METRICS, _id)
    assert parsed.vertical_range == MinimalRange(lower=0, upper=100)


def test_parse_graph_from_api_collapses_bidirectional_into_one_graph() -> None:
    # A bidirectional becomes a single graph: the upper half normal, the lower half inverse.
    bidir = graphs_v1.Bidirectional(
        name="b",
        title=Title("title"),
        lower=graphs_v1.Graph(name="lo", title=Title("lo"), compound_lines=["a"]),
        upper=graphs_v1.Graph(name="up", title=Title("up"), compound_lines=["b"]),
    )
    assert parse_graph_from_api(bidir, _SERVICE, _METRICS, _id) == DiscoveredGraph(
        name="b",
        title="title",
        stacks=[
            DiscoveredStack(members=[_rrd("b")], inverse=False),
            DiscoveredStack(members=[_rrd("a")], inverse=True),
        ],
        lines=[],
        rules=[],
    )


# --- concretize: DiscoveredGraph -> ConcreteGraph (resolve display) ------------------------------


def test_concretize_resolves_metric_curves_from_the_registry() -> None:
    discovered = parse_graph_from_api(
        graphs_v1.Graph(
            name="g",
            title=Title("Title"),
            compound_lines=["a", "b"],
            simple_lines=["c"],
        ),
        _SERVICE,
        _METRICS,
        _id,
    )
    assert concretize(discovered, _METRICS, _id) == ConcreteGraph(
        name="g",
        title="Title",
        stacks=[_stack(_curve(_rrd("a")), _curve(_rrd("b")))],
        lines=[_line(_rrd("c"))],
        rules=[],
    )


def test_concretize_resolves_threshold_rules_from_the_scalar_kind() -> None:
    discovered = parse_graph_from_api(
        graphs_v1.Graph(
            name="g",
            title=Title("t"),
            simple_lines=[
                metrics_v1.WarningOf("a"),
                metrics_v1.CriticalOf("a"),
                metrics_v1.MinimumOf("a", metrics_v1.Color.GREEN),
                metrics_v1.MaximumOf("a", metrics_v1.Color.RED),
            ],
        ),
        _SERVICE,
        _METRICS,
        _id,
    )
    concrete = concretize(discovered, _METRICS, _id)
    # warn / crit get their semantic label and the WARN / CRIT colour; min / max keep their
    # author-chosen colour (GREEN / RED), carried on the ScalarOf through the DiscoveredGraph.
    assert concrete.rules == [
        _rule(
            ScalarOf(metric=_rrd("a"), kind=ScalarKind.WARNING),
            CurveAttributes(title="Warning", unit=_DECIMAL, color=_WARN_COLOR),
        ),
        _rule(
            ScalarOf(metric=_rrd("a"), kind=ScalarKind.CRITICAL),
            CurveAttributes(title="Critical", unit=_DECIMAL, color=_CRIT_COLOR),
        ),
        _rule(
            ScalarOf(metric=_rrd("a"), kind=ScalarKind.MINIMUM, color="#15d1a0"),
            CurveAttributes(title="Minimum", unit=_DECIMAL, color="#15d1a0"),
        ),
        _rule(
            ScalarOf(metric=_rrd("a"), kind=ScalarKind.MAXIMUM, color="#ed3b3b"),
            CurveAttributes(title="Maximum", unit=_DECIMAL, color="#ed3b3b"),
        ),
    ]


def test_concretize_localizes_rule_labels() -> None:
    discovered = parse_graph_from_api(
        graphs_v1.Graph(name="g", title=Title("t"), simple_lines=[metrics_v1.WarningOf("a")]),
        _SERVICE,
        _METRICS,
        _id,
    )
    concrete = concretize(discovered, _METRICS, lambda s: f"<{s}>")
    assert [rule.curve.attributes.title for rule in concrete.rules] == ["<Warning>"]


def test_concretize_uses_the_fallback_colour_for_an_undefined_metric() -> None:
    discovered = parse_graph_from_api(
        graphs_v1.Graph(name="g", title=Title("t"), simple_lines=[metrics_v1.WarningOf("u")]),
        _SERVICE,
        {},
        _id,
    )
    concrete = concretize(discovered, {}, _id)
    # The WARN colour still applies; only the unit falls back to the dimensionless default.
    assert concrete.rules == [
        _rule(
            ScalarOf(metric=_rrd("u"), kind=ScalarKind.WARNING),
            CurveAttributes(title="Warning", unit=_DECIMAL, color=_WARN_COLOR),
        )
    ]


def test_concretize_reads_operation_display_from_the_quantity() -> None:
    discovered = parse_graph_from_api(
        graphs_v1.Graph(
            name="g",
            title=Title("t"),
            simple_lines=[metrics_v1.Sum(Title("s"), metrics_v1.Color.BLUE, ["a", "b"])],
        ),
        _SERVICE,
        _METRICS,
        _id,
    )
    concrete = concretize(discovered, _METRICS, _id)
    assert concrete.lines == [
        _line(
            Sum(
                summands=[_rrd("a"), _rrd("b")],
                display=CurveAttributes(title="s", unit=_DECIMAL, color="#28a2f3"),
            ),
            CurveAttributes(title="s", unit=_DECIMAL, color="#28a2f3"),
        )
    ]
