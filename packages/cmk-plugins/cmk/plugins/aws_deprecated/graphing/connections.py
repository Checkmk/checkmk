#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_current_connections = metrics.Metric(
    name="current_connections",
    title=Title("Current connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_new_connections = metrics.Metric(
    name="new_connections",
    title=Title("New connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)

graph_connection_count = graphs.Graph(
    name="connection_count",
    title=Title("Connections"),
    simple_lines=[
        "current_connections",
        "new_connections",
    ],
)
