#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph, MinimalRange
from cmk.graphing.v1.metrics import Color, Metric, TimeNotation, Unit
from cmk.graphing.v1.perfometers import (
    Bidirectional,
    Closed,
    FocusRange,
    Open,
    Perfometer,
)

UNIT_MILLISECOND = Unit(TimeNotation())


metric_corosync_latency_max = Metric(
    name="latency_max",
    title=Title("Maximum Latency"),
    unit=UNIT_MILLISECOND,
    color=Color.RED,
)

metric_corosync_latency_ave = Metric(
    name="latency_ave",
    title=Title("Average Latency"),
    unit=UNIT_MILLISECOND,
    color=Color.ORANGE,
)

graph_corosync_latency = Graph(
    name="corosync_latency_graph",
    title=Title("Corosync Latency max/avg"),
    simple_lines=["latency_max", "latency_ave"],
    minimal_range=MinimalRange(0.0, 0.05),
)

perfometer_corosync_latency = Bidirectional(
    name="corosync_latency_perf",
    left=Perfometer(
        name="latency_max",
        focus_range=FocusRange(Closed(0.0), Open(0.03)),
        segments=["latency_max"],
    ),
    right=Perfometer(
        name="latency_ave",
        focus_range=FocusRange(
            Closed(0.0),
            Open(0.03),
        ),
        segments=["latency_ave"],
    ),
)
