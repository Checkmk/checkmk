#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

metric_tcp_bound = metrics.Metric(
    name="tcp_bound",
    title=Title("State BOUND"),
    unit=metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2)),
    color=metrics.Color.DARK_CYAN,
)

metric_tcp_close_wait = metrics.Metric(
    name="tcp_close_wait",
    title=Title("State CLOSE_WAIT"),
    unit=metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2)),
    color=metrics.Color.DARK_PINK,
)

metric_tcp_closed = metrics.Metric(
    name="tcp_closed",
    title=Title("State CLOSED"),
    unit=metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2)),
    color=metrics.Color.YELLOW,
)

metric_tcp_closing = metrics.Metric(
    name="tcp_closing",
    title=Title("State CLOSING"),
    unit=metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2)),
    color=metrics.Color.LIGHT_BROWN,
)

metric_tcp_established = metrics.Metric(
    name="tcp_established",
    title=Title("State ESTABLISHED"),
    unit=metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2)),
    color=metrics.Color.GREEN,
)

metric_tcp_fin_wait1 = metrics.Metric(
    name="tcp_fin_wait1",
    title=Title("State FIN_WAIT1"),
    unit=metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2)),
    color=metrics.Color.LIGHT_GRAY,
)

metric_tcp_fin_wait2 = metrics.Metric(
    name="tcp_fin_wait2",
    title=Title("State FIN_WAIT2"),
    unit=metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2)),
    color=metrics.Color.DARK_GRAY,
)

metric_tcp_idle = metrics.Metric(
    name="tcp_idle",
    title=Title("State IDLE"),
    unit=metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2)),
    color=metrics.Color.BLUE,
)

metric_tcp_last_ack = metrics.Metric(
    name="tcp_last_ack",
    title=Title("State LAST_ACK"),
    unit=metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2)),
    color=metrics.Color.PURPLE,
)

metric_tcp_listen = metrics.Metric(
    name="tcp_listen",
    title=Title("State LISTEN"),
    unit=metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2)),
    color=metrics.Color.DARK_BLUE,
)

metric_tcp_syn_recv = metrics.Metric(
    name="tcp_syn_recv",
    title=Title("State SYN_RECV"),
    unit=metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2)),
    color=metrics.Color.RED,
)

metric_tcp_syn_sent = metrics.Metric(
    name="tcp_syn_sent",
    title=Title("State SYN_SENT"),
    unit=metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2)),
    color=metrics.Color.DARK_RED,
)

metric_tcp_time_wait = metrics.Metric(
    name="tcp_time_wait",
    title=Title("State TIME_WAIT"),
    unit=metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2)),
    color=metrics.Color.DARK_CYAN,
)

perfometer_tcp_established = perfometers.Perfometer(
    name="tcp_established",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(50)),
    segments=["tcp_established"],
)

graph_tcp_connection_states = graphs.Graph(
    name="tcp_connection_states",
    title=Title("TCP connection states"),
    compound_lines=[
        "tcp_listen",
        "tcp_established",
        "tcp_time_wait",
        "tcp_bound",
        "tcp_close_wait",
        "tcp_closed",
        "tcp_closing",
        "tcp_fin_wait1",
        "tcp_fin_wait2",
        "tcp_idle",
        "tcp_last_ack",
        "tcp_syn_recv",
        "tcp_syn_sent",
    ],
    optional=[
        "tcp_bound",
        "tcp_idle",
    ],
)
