#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNT = metrics.Unit(metrics.DecimalNotation(""))

metric_azure_redis_expired_keys = metrics.Metric(
    name="azure_redis_expired_keys",
    title=Title("Expired keys"),
    unit=UNIT_COUNT,
    color=metrics.Color.CYAN,
)

graph_azure_redis_expired_keys = graphs.Graph(
    name="azure_redis_expired_keys",
    title=Title("Expired keys"),
    compound_lines=["azure_redis_expired_keys"],
)
