#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

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
