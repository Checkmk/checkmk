#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_requests = metrics.Metric(
    name="requests",
    title=Title("Requests per second"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)

perfometer_requests = perfometers.Perfometer(
    name="requests",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(200),
    ),
    segments=["requests"],
)

graph_requests = graphs.Graph(
    name="requests",
    title=Title("Requests"),
    simple_lines=["requests"],
)
