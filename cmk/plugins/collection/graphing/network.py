#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.SINotation("B/s"))
UNIT_BYTES_PER_REQUEST = metrics.Unit(metrics.SINotation("B/req"))
UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_clients_connected = metrics.Metric(
    name="clients_connected",
    title=Title("Clients connected"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_data_transfer_rate = metrics.Metric(
    name="data_transfer_rate",
    title=Title("Data transfer rate"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

metric_request_transfer_rate = metrics.Metric(
    name="request_transfer_rate",
    title=Title("Request transfer rate"),
    unit=UNIT_BYTES_PER_REQUEST,
    color=metrics.Color.LIGHT_GREEN,
)

metric_active_connections = metrics.Metric(
    name="active_connections",
    title=Title("Active connections"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_idle_connections = metrics.Metric(
    name="idle_connections",
    title=Title("Idle connections"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

graph_db_connections = graphs.Graph(
    name="db_connections",
    title=Title("DB Connections"),
    simple_lines=[
        "active_connections",
        "idle_connections",
        metrics.WarningOf("active_connections"),
        metrics.CriticalOf("active_connections"),
    ],
)

metric_idle_workers = metrics.Metric(
    name="idle_workers",
    title=Title("Idle workers"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

metric_idle_servers = metrics.Metric(
    name="idle_servers",
    title=Title("Idle servers"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)

metric_busy_workers = metrics.Metric(
    name="busy_workers",
    title=Title("Busy workers"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)

metric_busy_servers = metrics.Metric(
    name="busy_servers",
    title=Title("Busy servers"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_GRAY,
)

graph_busy_and_idle_workers = graphs.Graph(
    name="busy_and_idle_workers",
    title=Title("Busy and idle workers"),
    compound_lines=[
        "busy_workers",
        "idle_workers",
    ],
)

graph_busy_and_idle_servers = graphs.Graph(
    name="busy_and_idle_servers",
    title=Title("Busy and idle servers"),
    compound_lines=[
        "busy_servers",
        "idle_servers",
    ],
)

metric_open_slots = metrics.Metric(
    name="open_slots",
    title=Title("Open slots"),
    unit=UNIT_NUMBER,
    color=metrics.Color.CYAN,
)

metric_total_slots = metrics.Metric(
    name="total_slots",
    title=Title("Total slots"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BROWN,
)

graph_total_and_open_slots = graphs.Graph(
    name="total_and_open_slots",
    title=Title("Total and open slots"),
    compound_lines=["total_slots"],
    simple_lines=["open_slots"],
)

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

metric_open_network_sockets = metrics.Metric(
    name="open_network_sockets",
    title=Title("Open network sockets"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

graph_web_gateway_miscellaneous_statistics = graphs.Graph(
    name="web_gateway_miscellaneous_statistics",
    title=Title("Web gateway miscellaneous statistics"),
    compound_lines=[
        "open_network_sockets",
        "connections",
    ],
)

perfometer_busy_workers_requests_per_second = perfometers.Stacked(
    name="busy_workers_requests_per_second",
    lower=perfometers.Perfometer(
        name="busy_workers",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(20)),
        segments=["busy_workers"],
    ),
    upper=perfometers.Perfometer(
        name="requests_per_second",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(20)),
        segments=["requests_per_second"],
    ),
)

perfometer_op_s = perfometers.Perfometer(
    name="op_s",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(1000)),
    segments=["op_s"],
)
