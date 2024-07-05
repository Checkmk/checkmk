#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_connections_conn_threads = metrics.Metric(
    name="connections_conn_threads",
    title=Title("Currently open connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_connections_max = metrics.Metric(
    name="connections_max",
    title=Title("Maximum parallel connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_connections_max_used = metrics.Metric(
    name="connections_max_used",
    title=Title("Maximum used parallel connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)

graph_DB_connections = graphs.Graph(
    name="DB_connections",
    title=Title("Parallel connections"),
    simple_lines=[
        "connections_max_used",
        "connections_conn_threads",
        "connections_max",
    ],
)
