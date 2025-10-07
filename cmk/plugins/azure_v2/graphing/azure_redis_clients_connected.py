#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNT = metrics.Unit(metrics.DecimalNotation(""))


metric_azure_redis_clients_connected = metrics.Metric(
    name="azure_redis_clients_connected",
    title=Title("Connected clients"),
    unit=UNIT_COUNT,
    color=metrics.Color.PURPLE,
)


graph_azure_redis_clients_connected = graphs.Graph(
    name="azure_redis_clients_connected",
    title=Title("Connected Clients"),
    compound_lines=[
        "azure_redis_clients_connected",
    ],
)
