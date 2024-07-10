#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_average_latency_cmk = metrics.Metric(
    name="average_latency_cmk",
    title=Title("Checkmk checker latency"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_average_latency_fetcher = metrics.Metric(
    name="average_latency_fetcher",
    title=Title("Checkmk fetcher latency"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_YELLOW,
)
metric_average_latency_generic = metrics.Metric(
    name="average_latency_generic",
    title=Title("Active check latency"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)

graph_average_helper_latency = graphs.Graph(
    name="average_helper_latency",
    title=Title("Average helper latency"),
    simple_lines=[
        "average_latency_fetcher",
        "average_latency_cmk",
        "average_latency_generic",
    ],
)
