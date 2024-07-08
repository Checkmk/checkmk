#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_disk_read_latency = metrics.Metric(
    name="disk_read_latency",
    title=Title("Disk read latency"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_disk_write_latency = metrics.Metric(
    name="disk_write_latency",
    title=Title("Disk write latency"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)

graph_disk_rw_latency = graphs.Bidirectional(
    name="disk_rw_latency",
    title=Title("Disk latency"),
    lower=graphs.Graph(
        name="disk_rw_latency_lower",
        title=Title("Disk latency"),
        compound_lines=["disk_write_latency"],
    ),
    upper=graphs.Graph(
        name="disk_rw_latency_upper",
        title=Title("Disk latency"),
        compound_lines=["disk_read_latency"],
    ),
)
