#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_disk_io_utilization = metrics.Metric(
    name="disk_io_utilization",
    title=Title("Disk IO Utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)

perfometer_disk_io_utilization = perfometers.Perfometer(
    name="disk_io_utilization",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=["disk_io_utilization"],
)

graph_disk_io_utilization = graphs.Graph(
    name="disk_io_utilization",
    title=Title("Disk IO Utilization"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=["disk_io_utilization"],
    simple_lines=[
        metrics.WarningOf("disk_io_utilization"),
        metrics.CriticalOf("disk_io_utilization"),
    ],
)
