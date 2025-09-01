#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

# We don't use the more general "memory_util" mostly because we want to be able
# explicitly set the order of the Azure graphs in
# cmk/gui/graphing/_graphs_order.py, and "memory_util" doesn't supply an
# explicit Graph.
metric_azure_redis_memory_utilization = metrics.Metric(
    name="azure_redis_memory_utilization",
    title=Title("Memory utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)

perfometer_azure_redis_memory_utilization = perfometers.Perfometer(
    name="azure_redis_memory_utilization",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=["azure_redis_memory_utilization"],
)

graph_azure_redis_memory_utilization = graphs.Graph(
    name="azure_redis_memory_utilization",
    title=Title("Memory utilization"),
    compound_lines=["azure_redis_memory_utilization"],
)
