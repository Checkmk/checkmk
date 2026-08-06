#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing_engine import (
    AutoPrecision,
    ConsolidationFunction,
    Constant,
    Curve,
    CurveAttributes,
    DecimalNotation,
    FixedRange,
    Graph,
    HostName,
    Line,
    MetricName,
    RRDMetric,
    Rule,
    ScalarKind,
    ScalarOf,
    ServiceName,
    Stack,
    Sum,
    Unit,
)
from cmk.gui.graphing._engine_dispatch import serialize_graphs
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.rest_api_client import ClientRegistry


def _comprehensive_graph() -> Graph:
    # A graph exercising every serializable node type (FixedRange, Stack, Line, Rule, Sum, Constant,
    # ScalarOf, RRDMetric), so the round-trip through the ``internal`` Json request field covers the
    # full schema rather than just an empty envelope.
    unit = Unit(notation=DecimalNotation("X"), precision=AutoPrecision(2))
    rrd = RRDMetric(
        host_name=HostName("h"), service_name=ServiceName("s"), metric_name=MetricName("m")
    )
    attrs = CurveAttributes(title="m", unit=unit, color="#FFFFFF")
    return Graph(
        name="g",
        title="Title %(x)s",
        kind="template",
        vertical_range=FixedRange(
            lower=0, upper=ScalarOf(metric=rrd, scalar_kind=ScalarKind.MAXIMUM, color="#mx")
        ),
        stacks=[
            Stack(
                members=[
                    Curve(
                        quantity=Sum(
                            summands=[
                                rrd,
                                Constant(2, CurveAttributes(title="c", unit=unit, color="#c")),
                            ]
                        ),
                        attributes=attrs,
                    )
                ],
                inverse=True,
                reference=Curve(
                    quantity=RRDMetric(
                        host_name=HostName("h"),
                        service_name=ServiceName("s"),
                        metric_name=MetricName("ref"),
                        consolidation_function=ConsolidationFunction.MAX,
                    ),
                    attributes=attrs,
                ),
            )
        ],
        lines=[
            Line(
                curve=Curve(
                    quantity=ScalarOf(metric=rrd, scalar_kind=ScalarKind.WARNING, color="#w"),
                    attributes=attrs,
                ),
                inverse=False,
            )
        ],
        rules=[
            Rule(
                curve=Curve(
                    quantity=ScalarOf(metric=rrd, scalar_kind=ScalarKind.MAXIMUM, color="#mx"),
                    attributes=attrs,
                ),
                inverse=True,
            )
        ],
    )


def test_fetch_graph_data_comprehensive_graph(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table(
        "services",
        [
            {
                "host_name": "h",
                "description": "s",
                "check_command": "check_mk-x",
                "metrics": ["m", "ref"],
                "perf_data": "m=1;5;10;0;100 ref=2",
            }
        ],
    )
    mock_livestatus.expect_query(
        "GET services\nColumns: host_name description perf_data check_command\nFilter: host_name = h\nFilter: description = s\nAnd: 2"
    )
    mock_livestatus.expect_query(
        "GET services\nColumns: host_name description rrddata:m:m.average:0:60:10\nFilter: host_name = h\nFilter: description = s\nAnd: 2"
    )
    with mock_livestatus():
        resp = clients.Graph.fetch_data(
            internal=serialize_graphs([_comprehensive_graph()]),
            requested_time_range={"start": 0, "end": 60, "step": 10},
            consolidation_function="avg",
        )
    assert resp.status_code == 200
    unit = {
        "notation": "decimal",
        "symbol": "X",
        "precision": {"type": "auto", "digits": 2},
        "convertible": True,
    }

    def _metadata(name: str) -> dict[str, object]:
        return {"name": name, "title": "m", "unit": unit, "color": "#FFFFFF"}

    assert resp.json == {
        # The header reads the evaluated title, so the fetch is what carries it.
        "title": "Title %(x)s",
        "time_range": {"start": 0, "end": 60, "step": 10},
        "metrics": [
            {
                "metadata": _metadata("-rrd_metric(h/s/ref)"),
                "render": {"stack": "stack-0", "inverse": True, "hidden": True},
                "data_points": [None, None, None, None, None, None],
            },
            {
                "metadata": _metadata("-sum(rrd_metric(h/s/m),constant(2))"),
                "render": {"stack": "stack-0", "inverse": True, "hidden": False},
                "data_points": [2.0, 2.0, 2.0, 2.0, 2.0, 2.0],
            },
            {
                "metadata": _metadata("scalar_of(warning,rrd_metric(h/s/m))"),
                "render": {"stack": None, "inverse": False, "hidden": False},
                "data_points": [5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
            },
        ],
        "horizontal_lines": [
            {
                "name": "-scalar_of(maximum,rrd_metric(h/s/m))",
                # This graph gives every curve explicit attributes, so the line is titled by them
                # rather than by what the scalar would resolve to.
                "title": "m",
                "value": -100.0,
                "unit": unit,
                "color": "#FFFFFF",
            }
        ],
        "warnings": [],
        "errors": [],
    }
