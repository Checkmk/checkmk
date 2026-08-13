#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_faas_memory_size_absolute_50 = metrics.Metric(
    name="faas_memory_size_absolute_50",
    title=Title("Memory size (50th percentile)"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_faas_memory_size_absolute_95 = metrics.Metric(
    name="faas_memory_size_absolute_95",
    title=Title("Memory size (95th percentile)"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_faas_memory_size_absolute_99 = metrics.Metric(
    name="faas_memory_size_absolute_99",
    title=Title("Memory size (99th percentile)"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)

graph_faas_memory_size_absolute = graphs.Graph(
    name="faas_memory_size_absolute",
    title=Title("Memory size"),
    simple_lines=[
        "faas_memory_size_absolute_50",
        "faas_memory_size_absolute_95",
        "faas_memory_size_absolute_99",
    ],
)
