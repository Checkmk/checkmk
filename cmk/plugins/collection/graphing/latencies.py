#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_latencies_50 = metrics.Metric(
    name="latencies_50",
    title=Title("Latencies (50th percentile)"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_latencies_95 = metrics.Metric(
    name="latencies_95",
    title=Title("Latencies (95th percentile)"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_latencies_99 = metrics.Metric(
    name="latencies_99",
    title=Title("Latencies (99th percentile)"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)

graph_latencies = graphs.Graph(
    name="latencies",
    title=Title("Latencies"),
    simple_lines=[
        "latencies_50",
        "latencies_95",
        "latencies_99",
    ],
)
