#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_san_read_latency = metrics.Metric(
    name="san_read_latency",
    title=Title("SAN read latency"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_san_write_latency = metrics.Metric(
    name="san_write_latency",
    title=Title("SAN write latency"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)

graph_san_latency = graphs.Bidirectional(
    name="san_latency",
    title=Title("SAN latency"),
    lower=graphs.Graph(
        name="san_latency_lower",
        title=Title("SAN latency"),
        compound_lines=["san_read_latency"],
    ),
    upper=graphs.Graph(
        name="san_latency_upper",
        title=Title("SAN latency"),
        compound_lines=["san_write_latency"],
    ),
)
