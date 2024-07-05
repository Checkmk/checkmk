#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_server_latency = metrics.Metric(
    name="server_latency",
    title=Title("Server latency"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)

graph_server_latency = graphs.Graph(
    name="server_latency",
    title=Title("Server latency"),
    simple_lines=["server_latency"],
)
