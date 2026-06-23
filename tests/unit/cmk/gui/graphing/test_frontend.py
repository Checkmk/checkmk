#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.graphing_engine import (
    AutoPrecision,
    Curve,
    CurveAttributes,
    DecimalNotation,
    EngineeringScientificNotation,
    Graph,
    HostName,
    IECNotation,
    MetricName,
    RRDMetric,
    ServiceName,
    SINotation,
    Stack,
    StandardScientificNotation,
    TimeNotation,
    Unit,
)
from cmk.gui.graphing._engine_serialization import serialize_graphs
from cmk.gui.graphing._frontend import to_cmk_time_series_graph
from cmk.shared_typing.cmk_time_series_graph import GraphHeader, GraphOptions, Interaction, Size

_Notation = (
    DecimalNotation
    | SINotation
    | IECNotation
    | StandardScientificNotation
    | EngineeringScientificNotation
    | TimeNotation
)

_UNIT = Unit(notation=DecimalNotation("X"), precision=AutoPrecision(2))
_RRD = RRDMetric(
    host_name=HostName("h"), service_name=ServiceName("s"), metric_name=MetricName("m")
)
_SIZE = Size(width=800.0, height=200.0, mode="resizable")


def test_to_cmk_time_series_graph_shell() -> None:
    # The shell carries only what is derivable from the (unevaluated) definition plus the render
    # options. The header title/name come from the engine ``Graph`` itself, not from an evaluation.
    graph = Graph(
        name="mygraph",
        title="My Graph",
        graph_type="template",
        stacks=[
            Stack(
                members=[
                    Curve(
                        quantity=_RRD, attributes=CurveAttributes(title="m", unit=_UNIT, color="#m")
                    )
                ],
                inverse=False,
            )
        ],
    )
    result = to_cmk_time_series_graph(graph, size=_SIZE)

    assert result.size == _SIZE
    assert result.options == GraphOptions(
        header=GraphHeader(title="My Graph", show_graph_time=True),
        name="mygraph",
        x_axis=None,
        y_axis=None,
        show_pin=True,
        font_size_pt=8.0,
    )
    assert result.interaction == Interaction(
        burger="enabled", zoom="enabled", panning="enabled", hover="enabled"
    )
    # No evaluation happens here: the data (metrics/horizontal_lines) and the resampled range are
    # fetched separately, so the shell has a null time range.
    assert result.time_range is None
    assert result.graph_type == "template"
    # The internal field is the opaque JSON serialization of the graph definition envelope.
    assert result.internal == json.dumps(serialize_graphs([graph]))
