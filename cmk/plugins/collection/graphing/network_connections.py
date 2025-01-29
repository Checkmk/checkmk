#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_connections = metrics.Metric(
    name="connections",
    title=Title("Connections"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)
metric_connections_async_writing = metrics.Metric(
    name="connections_async_writing",
    title=Title("Asynchronous writing connections"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)
metric_connections_async_keepalive = metrics.Metric(
    name="connections_async_keepalive",
    title=Title("Asynchronous keep alive connections"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)
metric_connections_async_closing = metrics.Metric(
    name="connections_async_closing",
    title=Title("Asynchronous closing connections"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)
metric_open_network_sockets = metrics.Metric(
    name="open_network_sockets",
    title=Title("Open network sockets"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

perfometer_connections = perfometers.Perfometer(
    name="connections",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(90),
    ),
    segments=["connections"],
)

graph_connections = graphs.Graph(
    name="connections",
    title=Title("Connections"),
    compound_lines=["connections"],
    simple_lines=[
        "connections_async_writing",
        "connections_async_keepalive",
        "connections_async_closing",
        metrics.WarningOf("connections"),
        metrics.CriticalOf("connections"),
    ],
    optional=[
        "connections_async_writing",
        "connections_async_keepalive",
        "connections_async_closing",
    ],
)
graph_web_gateway_miscellaneous_statistics = graphs.Graph(
    name="web_gateway_miscellaneous_statistics",
    title=Title("Web gateway miscellaneous statistics"),
    compound_lines=[
        "open_network_sockets",
        "connections",
    ],
)
