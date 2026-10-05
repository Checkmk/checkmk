#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

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
