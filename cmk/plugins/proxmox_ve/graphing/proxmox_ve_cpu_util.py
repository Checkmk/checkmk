#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

metric_disk_read_throughput = metrics.Metric(
    name="cpu_core_usage",
    title=Title("CPU Core Usage"),
    unit=metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(digits=2)),
    color=metrics.Color.BLUE,
)

graph_cpu_usage = graphs.Graph(
    name="cpu_core_usage",
    title=Title("CPU Cores"),
    compound_lines=["cpu_core_usage"],
    simple_lines=[
        metrics.WarningOf("cpu_core_usage"),
        metrics.CriticalOf("cpu_core_usage"),
    ],
)
