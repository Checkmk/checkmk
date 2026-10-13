#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing_engine import (
    AutoPrecision,
    Curve,
    CurveAttributes,
    DecimalNotation,
    Graph,
    HostName,
    Line,
    MetricName,
    NonConvertibleUnit,
    RRDMetric,
    ServiceName,
    Stack,
    Unit,
)
from cmk.gui.graphing import BuiltGraph

_STACK_UNIT = Unit(notation=DecimalNotation("s"), precision=AutoPrecision(2))
_LINE_UNIT = Unit(notation=DecimalNotation("l"), precision=AutoPrecision(2))


def _curve(unit: Unit) -> Curve:
    return Curve(
        quantity=RRDMetric(
            host_name=HostName("h"), service_name=ServiceName("svc"), metric_name=MetricName("m")
        ),
        attributes=CurveAttributes(title="m", unit=unit, color="#111111"),
    )


def _graph(*, stacks: list[Stack] | None = None, lines: list[Line] | None = None) -> Graph:
    return Graph(name="g", title="g", kind="test", stacks=stacks or [], lines=lines or [])


def test_the_unit_the_graph_names_wins_over_its_curves() -> None:
    named = NonConvertibleUnit(notation=DecimalNotation("n"), precision=AutoPrecision(2))
    built = BuiltGraph(
        graph=_graph(lines=[Line(curve=_curve(_LINE_UNIT), inverse=False)]),
        specification=None,
        y_axis_unit=named,
    )

    assert built.resolved_y_axis_unit() == named


def test_an_unnamed_unit_is_the_one_of_the_first_drawn_curve() -> None:
    built = BuiltGraph(
        graph=_graph(
            stacks=[Stack(members=[_curve(_STACK_UNIT)], inverse=False)],
            lines=[Line(curve=_curve(_LINE_UNIT), inverse=False)],
        ),
        specification=None,
    )

    assert built.resolved_y_axis_unit() == _STACK_UNIT


def test_a_graph_without_curves_has_no_unit() -> None:
    built = BuiltGraph(graph=_graph(), specification=None)

    assert built.resolved_y_axis_unit() is None
