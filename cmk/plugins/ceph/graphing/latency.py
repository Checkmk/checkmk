#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())
UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_apply_latency = metrics.Metric(
    name="apply_latency",
    title=Title("Apply Latency"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)
metric_commit_latency = metrics.Metric(
    name="commit_latency",
    title=Title("Commit Latency"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)

graph_osd_latency_osd_latency = graphs.Bidirectional(
    name="osd_latency_osd_latency",
    title=Title("OSD Latency"),
    lower=graphs.Graph(
        name="osd_latency",
        title=Title("OSD Latency"),
        simple_lines=["commit_latency"],
    ),
    upper=graphs.Graph(
        name="osd_latency",
        title=Title("OSD Latency"),
        simple_lines=["apply_latency"],
    ),
)
