#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Color, graph, Localizable, metric, Unit

metric_load1 = metric.Metric(
    "load1",
    Localizable("CPU load average of last minute"),
    Unit.COUNT,
    Color.LIGHT_BLUE,
)

metric_load5 = metric.Metric(
    "load5",
    Localizable("CPU load average of last 5 minutes"),
    Unit.COUNT,
    Color.BLUE,
)

metric_load15 = metric.Metric(
    "load15",
    Localizable("CPU load average of last 15 minutes"),
    Unit.COUNT,
    Color.DARK_BLUE,
)

graph_cpu_load = graph.Graph(
    "cpu_load",
    Localizable("CPU Load - %(load1:max@count) CPU Cores"),
    compound_lines=["load1"],
    simple_lines=[
        "load5",
        "load15",
        metric.WarningOf("load15"),
        metric.CriticalOf("load15"),
    ],
    optional=["load5", "load15"],
)
