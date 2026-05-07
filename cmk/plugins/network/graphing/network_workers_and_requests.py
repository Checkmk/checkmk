#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_idle_workers = metrics.Metric(
    name="idle_workers",
    title=Title("Idle workers"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)
metric_busy_workers = metrics.Metric(
    name="busy_workers",
    title=Title("Busy workers"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)
metric_requests_per_second = metrics.Metric(
    name="requests_per_second",
    title=Title("Requests per second"),
    unit=metrics.Unit(metrics.DecimalNotation("req/s")),
    color=metrics.Color.GRAY,
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

graph_busy_and_idle_workers = graphs.Graph(
    name="busy_and_idle_workers",
    title=Title("Busy and idle workers"),
    compound_lines=[
        "busy_workers",
        "idle_workers",
    ],
)
