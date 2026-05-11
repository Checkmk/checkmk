#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_bar1_mem_usage_free = metrics.Metric(
    name="bar1_mem_usage_free",
    title=Title("BAR1 memory usage (free)"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_bar1_mem_usage_total = metrics.Metric(
    name="bar1_mem_usage_total",
    title=Title("BAR1 memory usage (total)"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_bar1_mem_usage_used = metrics.Metric(
    name="bar1_mem_usage_used",
    title=Title("BAR1 memory usage (used)"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)

graph_bar1_mem_usage = graphs.Graph(
    name="bar1_mem_usage",
    title=Title("BAR1 memory usage"),
    compound_lines=[
        "bar1_mem_usage_used",
        "bar1_mem_usage_free",
    ],
    simple_lines=["bar1_mem_usage_total"],
)
