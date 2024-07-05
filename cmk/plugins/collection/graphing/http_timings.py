#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_time_connect = metrics.Metric(
    name="time_connect",
    title=Title("Time to connect"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_time_firstbyte = metrics.Metric(
    name="time_firstbyte",
    title=Title("Time to receive start of response"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_time_headers = metrics.Metric(
    name="time_headers",
    title=Title("Time to send request"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_time_ssl = metrics.Metric(
    name="time_ssl",
    title=Title("Time to negotiate SSL"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_PINK,
)
metric_time_transfer = metrics.Metric(
    name="time_transfer",
    title=Title("Time to receive full response"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_response_time = metrics.Metric(
    name="response_time",
    title=Title("Response time"),
    unit=UNIT_TIME,
    color=metrics.Color.BROWN,
)

perfometer_response_time = perfometers.Perfometer(
    name="response_time",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(20),
    ),
    segments=["response_time"],
)

graph_http_timings = graphs.Graph(
    name="http_timings",
    title=Title("HTTP timings"),
    compound_lines=[
        "time_connect",
        "time_ssl",
        "time_headers",
        "time_transfer",
    ],
    simple_lines=[
        "time_firstbyte",
        "response_time",
    ],
    optional=["time_ssl"],
)
