#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_SECOND = metrics.Unit(metrics.TimeNotation())

metric_azure_redis_latency_serverside = metrics.Metric(
    name="azure_redis_latency_serverside",
    title=Title("Server side command latency"),
    unit=UNIT_SECOND,
    color=metrics.Color.YELLOW,
)

metric_azure_redis_latency_internode = metrics.Metric(
    name="azure_redis_latency_internode",
    title=Title("Cache internode latency"),
    unit=UNIT_SECOND,
    color=metrics.Color.GREEN,
)


graph_azure_redis_latency = graphs.Graph(
    name="azure_redis_latency",
    title=Title("Latency"),
    simple_lines=["azure_redis_latency_serverside", "azure_redis_latency_internode"],
)
