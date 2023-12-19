#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Color, graphs, Localizable, metrics, Unit

metric_load1 = metrics.Metric(
    name="load1",
    title=Localizable("CPU load average of last minute"),
    unit=Unit.COUNT,
    color=Color.LIGHT_BLUE,
)

metric_load5 = metrics.Metric(
    name="load5",
    title=Localizable("CPU load average of last 5 minutes"),
    unit=Unit.COUNT,
    color=Color.BLUE,
)

metric_load15 = metrics.Metric(
    name="load15",
    title=Localizable("CPU load average of last 15 minutes"),
    unit=Unit.COUNT,
    color=Color.DARK_BLUE,
)

graph_cpu_load = graphs.Graph(
    name="cpu_load",
    title=Localizable("CPU Load - %(load1:max@count) CPU Cores"),
    compound_lines=["load1"],
    simple_lines=[
        "load5",
        "load15",
        metrics.WarningOf("load15"),
        metrics.CriticalOf("load15"),
    ],
    optional=["load5", "load15"],
)
