#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

metric_active_connections = metrics.Metric(
    name="active_connections",
    title=Title("Active connections"),
    unit=metrics.Unit.COUNT,
    color=metrics.Color.PURPLE,
)

metric_idle_connections = metrics.Metric(
    name="idle_connections",
    title=Title("Idle connections"),
    unit=metrics.Unit.COUNT,
    color=metrics.Color.DARK_PURPLE,
)

graph_db_connections = graphs.Graph(
    name="db_connections",
    title=Title("DB Connections"),
    simple_lines=[
        "active_connections",
        "idle_connections",
        metrics.WarningOf("active_connections"),
        metrics.CriticalOf("active_connections"),
    ],
)
