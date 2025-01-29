#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))

metric_disk_read_throughput = metrics.Metric(
    name="disk_read_throughput",
    title=Title("Read throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.GREEN,
)

metric_disk_write_throughput = metrics.Metric(
    name="disk_write_throughput",
    title=Title("Write throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
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

graph_disk_throughput = graphs.Bidirectional(
    name="disk_throughput",
    title=Title("Disk throughput"),
    lower=graphs.Graph(
        name="disk_write_throughput",
        title=Title("Write throughput"),
        compound_lines=["disk_write_throughput"],
        simple_lines=[
            metrics.WarningOf("disk_write_throughput"),
            metrics.CriticalOf("disk_write_throughput"),
        ],
    ),
    upper=graphs.Graph(
        name="disk_read_throughput",
        title=Title("Read throughput"),
        compound_lines=["disk_read_throughput"],
        simple_lines=[
            metrics.WarningOf("disk_read_throughput"),
            metrics.CriticalOf("disk_read_throughput"),
        ],
    ),
)
