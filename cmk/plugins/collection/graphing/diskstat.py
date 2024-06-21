#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""))

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_disk_read_throughput = metrics.Metric(
    name="disk_read_throughput",
    title=Title("Read throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)

metric_disk_write_throughput = metrics.Metric(
    name="disk_write_throughput",
    title=Title("Write throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.GREEN,
)

metric_disk_read_ios = metrics.Metric(
    name="disk_read_ios",
    title=Title("Read operations"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)

metric_disk_write_ios = metrics.Metric(
    name="disk_write_ios",
    title=Title("Write operations"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

metric_disk_average_read_wait = metrics.Metric(
    name="disk_average_read_wait",
    title=Title("Read wait time"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)

metric_disk_average_write_wait = metrics.Metric(
    name="disk_average_write_wait",
    title=Title("Write wait time"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)

metric_disk_average_wait = metrics.Metric(
    name="disk_average_wait",
    title=Title("Request wait time"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)

metric_disk_average_read_request_size = metrics.Metric(
    name="disk_average_read_request_size",
    title=Title("Average read request size"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)

metric_disk_average_write_request_size = metrics.Metric(
    name="disk_average_write_request_size",
    title=Title("Average write request size"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)

metric_disk_average_request_size = metrics.Metric(
    name="disk_average_request_size",
    title=Title("Average request size"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)

metric_disk_latency = metrics.Metric(
    name="disk_latency",
    title=Title("Average disk latency"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_PINK,
)

metric_disk_queue_length = metrics.Metric(
    name="disk_queue_length",
    title=Title("Average disk I/O-queue length"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)

metric_disk_utilization = metrics.Metric(
    name="disk_utilization",
    title=Title("Disk utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)

perfometer_disk_throughput = perfometers.Bidirectional(
    name="disk_throughput",
    left=perfometers.Perfometer(
        name="disk_read_throughput",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(9000000)),
        segments=["disk_read_throughput"],
    ),
    right=perfometers.Perfometer(
        name="disk_write_throughput",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(9000000)),
        segments=["disk_write_throughput"],
    ),
)

perfometer_disk_ios = perfometers.Bidirectional(
    name="disk_ios",
    left=perfometers.Perfometer(
        name="disk_read_ios",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(200000)),
        segments=["disk_read_ios"],
    ),
    right=perfometers.Perfometer(
        name="disk_write_ios",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(200000)),
        segments=["disk_write_ios"],
    ),
)

graph_disk_utilization = graphs.Graph(
    name="disk_utilization",
    title=Title("Disk utilization"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=["disk_utilization"],
    simple_lines=[
        metrics.WarningOf("disk_utilization"),
        metrics.CriticalOf("disk_utilization"),
    ],
)

graph_disk_throughput = graphs.Bidirectional(
    name="disk_throughput",
    title=Title("Disk throughput"),
    lower=graphs.Graph(
        name="disk_read_throughput",
        title=Title("Read throughput"),
        compound_lines=["disk_read_throughput"],
        simple_lines=[
            metrics.WarningOf("disk_read_throughput"),
            metrics.CriticalOf("disk_read_throughput"),
        ],
    ),
    upper=graphs.Graph(
        name="disk_write_throughput",
        title=Title("Write throughput"),
        compound_lines=["disk_write_throughput"],
        simple_lines=[
            metrics.WarningOf("disk_write_throughput"),
            metrics.CriticalOf("disk_write_throughput"),
        ],
    ),
)

graph_disk_io_operations = graphs.Bidirectional(
    name="disk_io_operations",
    title=Title("Disk I/O operations"),
    lower=graphs.Graph(
        name="disk_write_ios",
        title=Title("Disk write I/O operations"),
        compound_lines=["disk_write_ios"],
    ),
    upper=graphs.Graph(
        name="disk_read_ios",
        title=Title("Disk read I/O operations"),
        compound_lines=["disk_read_ios"],
    ),
)

graph_average_request_size = graphs.Bidirectional(
    name="average_request_size",
    title=Title("Average request size"),
    lower=graphs.Graph(
        name="disk_average_write_request_size",
        title=Title("Average request size"),
        compound_lines=["disk_average_write_request_size"],
    ),
    upper=graphs.Graph(
        name="disk_average_read_request_size",
        title=Title("Average request size"),
        compound_lines=["disk_average_read_request_size"],
    ),
)

graph_average_end_to_end_wait_time = graphs.Bidirectional(
    name="average_end_to_end_wait_time",
    title=Title("Average end to end wait time"),
    lower=graphs.Graph(
        name="disk_average_write_wait",
        title=Title("Average end to end wait time"),
        compound_lines=["disk_average_write_wait"],
    ),
    upper=graphs.Graph(
        name="disk_average_read_wait",
        title=Title("Average end to end wait time"),
        compound_lines=["disk_average_read_wait"],
    ),
)
