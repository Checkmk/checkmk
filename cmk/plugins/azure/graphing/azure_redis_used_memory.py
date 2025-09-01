#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_azure_redis_used_memory = metrics.Metric(
    name="azure_redis_used_memory",
    title=Title("Used memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)

metric_azure_redis_used_memory_rss = metrics.Metric(
    name="azure_redis_used_memory_rss",
    title=Title("Used memory RSS"),
    unit=UNIT_BYTES,
    color=metrics.Color.PINK,
)

graph_azure_redis_used_memory = graphs.Graph(
    name="azure_redis_used_memory",
    title=Title("Memory"),
    simple_lines=["azure_redis_used_memory"],
    compound_lines=["azure_redis_used_memory_rss"],
)
