#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_SECONDS_PER_SECOND = metrics.Unit(metrics.DecimalNotation("s/s"))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_faas_active_instance_count = metrics.Metric(
    name="faas_active_instance_count",
    title=Title("Number of active instances"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_PINK,
)
metric_faas_execution_count = metrics.Metric(
    name="faas_execution_count",
    title=Title("Number of requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_faas_execution_count_2xx = metrics.Metric(
    name="faas_execution_count_2xx",
    title=Title("Number of requests with return code class 2xx (success)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
metric_faas_execution_count_3xx = metrics.Metric(
    name="faas_execution_count_3xx",
    title=Title("Number of requests with return code class 3xx (redirection)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
metric_faas_execution_count_4xx = metrics.Metric(
    name="faas_execution_count_4xx",
    title=Title("Number of requests with return code class 4xx (client error)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_faas_execution_count_5xx = metrics.Metric(
    name="faas_execution_count_5xx",
    title=Title("Number of requests with return code class 5xx (server error)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
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
metric_faas_execution_times_3xx_50 = metrics.Metric(
    name="faas_execution_times_3xx_50",
    title=Title("Request latency with return code class 3xx (redirection) (50th percentile)"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_faas_execution_times_3xx_95 = metrics.Metric(
    name="faas_execution_times_3xx_95",
    title=Title("Request latency with return code class 3xx (redirection) (95th percentile)"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_faas_execution_times_3xx_99 = metrics.Metric(
    name="faas_execution_times_3xx_99",
    title=Title("Request latency with return code class 3xx (redirection) (99th percentile)"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_faas_execution_times_4xx_50 = metrics.Metric(
    name="faas_execution_times_4xx_50",
    title=Title("Request latency with return code class 4xx (client error) (50th percentile)"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_faas_execution_times_4xx_95 = metrics.Metric(
    name="faas_execution_times_4xx_95",
    title=Title("Request latency with return code class 4xx (client error) (95th percentile)"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_faas_execution_times_4xx_99 = metrics.Metric(
    name="faas_execution_times_4xx_99",
    title=Title("Request latency with return code class 4xx (client error) (99th percentile)"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_faas_execution_times_50 = metrics.Metric(
    name="faas_execution_times_50",
    title=Title("Request latency (50th percentile)"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_faas_execution_times_5xx_50 = metrics.Metric(
    name="faas_execution_times_5xx_50",
    title=Title("Request latency with return code class 5xx (server error) (50th percentile)"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_faas_execution_times_5xx_95 = metrics.Metric(
    name="faas_execution_times_5xx_95",
    title=Title("Request latency with return code class 5xx (server error) (95th percentile)"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_faas_execution_times_5xx_99 = metrics.Metric(
    name="faas_execution_times_5xx_99",
    title=Title("Request latency with return code class 5xx (server error) (99th percentile)"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_faas_execution_times_95 = metrics.Metric(
    name="faas_execution_times_95",
    title=Title("Request latency (95th percentile)"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_faas_execution_times_99 = metrics.Metric(
    name="faas_execution_times_99",
    title=Title("Request latency (99th percentile)"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_faas_memory_size_absolute_50 = metrics.Metric(
    name="faas_memory_size_absolute_50",
    title=Title("Memory Size (50th percentile)"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_faas_memory_size_absolute_95 = metrics.Metric(
    name="faas_memory_size_absolute_95",
    title=Title("Memory Size (95th percentile)"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_faas_memory_size_absolute_99 = metrics.Metric(
    name="faas_memory_size_absolute_99",
    title=Title("Memory Size (99th percentile)"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_faas_total_instance_count = metrics.Metric(
    name="faas_total_instance_count",
    title=Title("Total number of instances"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_gcp_billable_time = metrics.Metric(
    name="gcp_billable_time",
    title=Title("Billable time"),
    unit=UNIT_SECONDS_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)

graph_faas_execution_times = graphs.Graph(
    name="faas_execution_times",
    title=Title("Request latencies"),
    simple_lines=[
        "faas_execution_times_50",
        "faas_execution_times_95",
        "faas_execution_times_99",
    ],
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
graph_faas_execution_times_3xx = graphs.Graph(
    name="faas_execution_times_3xx",
    title=Title("Request latencies with return code class 3xx (redirection)"),
    simple_lines=[
        "faas_execution_times_3xx_50",
        "faas_execution_times_3xx_95",
        "faas_execution_times_3xx_99",
    ],
)
graph_faas_execution_times_4xx = graphs.Graph(
    name="faas_execution_times_4xx",
    title=Title("Request latencies with return code class 4xx (client error)"),
    simple_lines=[
        "faas_execution_times_4xx_50",
        "faas_execution_times_4xx_95",
        "faas_execution_times_4xx_99",
    ],
)
graph_faas_execution_times_5xx = graphs.Graph(
    name="faas_execution_times_5xx",
    title=Title("Request latencies with return code class 5xx (server error)"),
    simple_lines=[
        "faas_execution_times_5xx_50",
        "faas_execution_times_5xx_95",
        "faas_execution_times_5xx_99",
    ],
)
graph_faas_memory_size_absolute = graphs.Graph(
    name="faas_memory_size_absolute",
    title=Title("Memory Size"),
    simple_lines=[
        "faas_memory_size_absolute_50",
        "faas_memory_size_absolute_95",
        "faas_memory_size_absolute_99",
    ],
)
