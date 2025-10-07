#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))

metric_azure_redis_throughput_read = metrics.Metric(
    name="azure_redis_throughput_cache_read",
    title=Title("Read"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.GREEN,
)

metric_azure_redis_throughput_write = metrics.Metric(
    name="azure_redis_throughput_cache_write",
    title=Title("Write"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)

perfometer_azure_redis_throughput = perfometers.Bidirectional(
    name="azure_redis_throughput",
    left=perfometers.Perfometer(
        name="azure_redis_throughput_cache_read",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(1000000),
        ),
        segments=["azure_redis_throughput_cache_read"],
    ),
    right=perfometers.Perfometer(
        name="azure_redis_throughput_cache_write",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(1000000),
        ),
        segments=["azure_redis_throughput_cache_write"],
    ),
)

graph_azure_redis_throughput = graphs.Bidirectional(
    name="azure_redis_throughput",
    title=Title("Throughput"),
    upper=graphs.Graph(
        name="azure_redis_throughput_cache_read",
        title=Title("Read"),
        compound_lines=["azure_redis_throughput_cache_read"],
    ),
    lower=graphs.Graph(
        name="azure_redis_throughput_cache_write",
        title=Title("Write"),
        compound_lines=["azure_redis_throughput_cache_write"],
    ),
)
