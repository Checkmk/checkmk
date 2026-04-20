#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_faas_execution_times_2xx_50 = metrics.Metric(
    name="faas_execution_times_2xx_50",
    title=Title("Request latency with return code class 2xx (success) (50th percentile)"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_faas_execution_times_2xx_95 = metrics.Metric(
    name="faas_execution_times_2xx_95",
    title=Title("Request latency with return code class 2xx (success) (95th percentile)"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_faas_execution_times_2xx_99 = metrics.Metric(
    name="faas_execution_times_2xx_99",
    title=Title("Request latency with return code class 2xx (success) (99th percentile)"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)

graph_faas_execution_times_2xx = graphs.Graph(
    name="faas_execution_times_2xx",
    title=Title("Request latencies with return code class 2xx (success)"),
    simple_lines=[
        "faas_execution_times_2xx_50",
        "faas_execution_times_2xx_95",
        "faas_execution_times_2xx_99",
    ],
)
