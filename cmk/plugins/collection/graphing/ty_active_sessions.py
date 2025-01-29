#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_icmp_active_sessions = metrics.Metric(
    name="icmp_active_sessions",
    title=Title("Active ICMP sessions"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_sslproxy_active_sessions = metrics.Metric(
    name="sslproxy_active_sessions",
    title=Title("Active SSL proxy sessions"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_tcp_active_sessions = metrics.Metric(
    name="tcp_active_sessions",
    title=Title("Active TCP sessions"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BROWN,
)
metric_udp_active_sessions = metrics.Metric(
    name="udp_active_sessions",
    title=Title("Active UDP sessions"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

perfometer_tcp_active_sessions_udp_active_sessions = perfometers.Bidirectional(
    name="tcp_active_sessions_udp_active_sessions",
    left=perfometers.Perfometer(
        name="tcp_active_sessions",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(6),
        ),
        segments=["tcp_active_sessions"],
    ),
    right=perfometers.Perfometer(
        name="udp_active_sessions",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(6),
        ),
        segments=["udp_active_sessions"],
    ),
)

graph_palo_alto_sessions = graphs.Graph(
    name="palo_alto_sessions",
    title=Title("Palo Alto sessions"),
    compound_lines=[
        "tcp_active_sessions",
        "udp_active_sessions",
        "icmp_active_sessions",
        "sslproxy_active_sessions",
    ],
)
