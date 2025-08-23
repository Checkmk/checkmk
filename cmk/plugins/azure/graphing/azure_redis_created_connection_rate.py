#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))


metric_azure_redis_created_connection_rate = metrics.Metric(
    name="azure_redis_created_connection_rate",
    title=Title("Connections created rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)

metric_azure_redis_closed_connection_rate = metrics.Metric(
    name="azure_redis_closed_connection_rate",
    title=Title("Connections closed rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.RED,
)

graph_azure_redis_connections = graphs.Graph(
    name="azure_redis_connections",
    title=Title("Connections"),
    simple_lines=["azure_redis_created_connection_rate", "azure_redis_closed_connection_rate"],
)
