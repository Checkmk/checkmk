#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: is this still used?

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_read_latency = metrics.Metric(
    name="read_latency",
    title=Title("Read latency"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_write_latency = metrics.Metric(
    name="write_latency",
    title=Title("Write latency"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)

perfometer_write_latency_read_latency = perfometers.Stacked(
    name="write_latency_read_latency",
    lower=perfometers.Perfometer(
        name="write_latency",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(8),
        ),
        segments=["write_latency"],
    ),
    upper=perfometers.Perfometer(
        name="read_latency",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(8),
        ),
        segments=["read_latency"],
    ),
)

graph_disk_latency = graphs.Bidirectional(
    name="disk_latency",
    title=Title("Disk latency"),
    lower=graphs.Graph(
        name="disk_latency_lower",
        title=Title("Disk latency"),
        compound_lines=["write_latency"],
    ),
    upper=graphs.Graph(
        name="disk_latency_upper",
        title=Title("Disk latency"),
        compound_lines=["read_latency"],
    ),
)
