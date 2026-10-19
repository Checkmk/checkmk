#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from cmk.graphing_engine import (
    AutoPrecision,
    Curve,
    CurveAttributes,
    DecimalNotation,
    drawn_curves,
    DrawnCurve,
    Graph,
    HostName,
    Line,
    MetricName,
    RRDMetric,
    ServiceName,
    Stack,
    Unit,
)

_UNIT = Unit(notation=DecimalNotation(""), precision=AutoPrecision(2))


def _curve(name: str) -> Curve:
    return Curve(
        quantity=RRDMetric(
            host_name=HostName("h"),
            service_name=ServiceName("svc"),
            metric_name=MetricName(name),
        ),
        attributes=CurveAttributes(title=name, unit=_UNIT, color="#111111"),
    )


def _drawn(curves: Iterable[DrawnCurve[Curve]]) -> list[tuple[str, str, bool, str | None]]:
    return [
        (
            drawn.curve.attributes.title,
            drawn.line_type,
            drawn.mirrored,
            drawn.stack,
        )
        for drawn in curves
    ]


def test_the_curve_that_opens_a_stack_is_the_area_and_the_rest_pile_onto_it() -> None:
    graph = Graph(
        name="g",
        title="t",
        kind="test",
        stacks=[Stack(members=[_curve("a"), _curve("b")], inverse=False)],
        lines=[Line(curve=_curve("c"), inverse=False)],
    )

    assert _drawn(drawn_curves(graph.stacks, graph.lines)) == [
        ("a", "area", False, "stack-0"),
        ("b", "stack", False, "stack-0"),
        ("c", "line", False, None),
    ]


def test_a_mirrored_stack_and_line_report_their_mirroring() -> None:
    graph = Graph(
        name="g",
        title="t",
        kind="test",
        stacks=[Stack(members=[_curve("a")], inverse=True)],
        lines=[Line(curve=_curve("b"), inverse=True)],
    )

    assert _drawn(drawn_curves(graph.stacks, graph.lines)) == [
        ("a", "area", True, "stack-0"),
        ("b", "line", True, None),
    ]


def test_every_stack_gets_its_own_identifier() -> None:
    graph = Graph(
        name="g",
        title="t",
        kind="test",
        stacks=[
            Stack(members=[_curve("a")], inverse=False),
            Stack(members=[_curve("b")], inverse=False),
        ],
    )

    assert [drawn.stack for drawn in drawn_curves(graph.stacks, graph.lines)] == [
        "stack-0",
        "stack-1",
    ]
