#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_e2e_latency = metrics.Metric(
    name="e2e_latency",
    title=Title("End-to-end latency"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_YELLOW,
)

graph_e2e_latency = graphs.Graph(
    name="e2e_latency",
    title=Title("End-to-end latency"),
    simple_lines=["e2e_latency"],
)
