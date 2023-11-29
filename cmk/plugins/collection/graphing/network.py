#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Color, graph, Localizable, metric, Unit

metric_active_connections = metric.Metric(
    "active_connections",
    Localizable("Active connections"),
    Unit.COUNT,
    Color.DARK_ORCHID,
)

metric_idle_connections = metric.Metric(
    "idle_connections",
    Localizable("Idle connections"),
    Unit.COUNT,
    Color.MEDIUM_PURPLE,
)

graph_db_connections = graph.Graph(
    "db_connections",
    Localizable("DB Connections"),
    simple_lines=[
        "active_connections",
        "idle_connections",
        metric.WarningOf("active_connections"),
        metric.CriticalOf("active_connections"),
    ],
)
