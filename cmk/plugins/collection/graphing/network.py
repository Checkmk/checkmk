#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Color, graph, Localizable, metric, Unit

metric_active_connections = metric.Metric(
    name="active_connections",
    title=Localizable("Active connections"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_idle_connections = metric.Metric(
    name="idle_connections",
    title=Localizable("Idle connections"),
    unit=Unit.COUNT,
    color=Color.DARK_PURPLE,
)

graph_db_connections = graph.Graph(
    name="db_connections",
    title=Localizable("DB Connections"),
    simple_lines=[
        "active_connections",
        "idle_connections",
        metric.WarningOf("active_connections"),
        metric.CriticalOf("active_connections"),
    ],
)
