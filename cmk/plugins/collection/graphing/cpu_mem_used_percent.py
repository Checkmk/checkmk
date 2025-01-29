#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_cpu_mem_used_percent = metrics.Metric(
    name="cpu_mem_used_percent",
    title=Title("CPU Memory used"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)

perfometer_cpu_mem_used_percent = perfometers.Perfometer(
    name="cpu_mem_used_percent",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=["cpu_mem_used_percent"],
)

graph_cpu_mem_used_percent = graphs.Graph(
    name="cpu_mem_used_percent",
    title=Title("Used CPU memory"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=["cpu_mem_used_percent"],
    simple_lines=[
        metrics.WarningOf("cpu_mem_used_percent"),
        metrics.CriticalOf("cpu_mem_used_percent"),
    ],
)
