#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_threads = metrics.Metric(
    name="threads",
    title=Title("Threads"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_threads_daemon = metrics.Metric(
    name="threads_daemon",
    title=Title("Daemon threads"),
    unit=UNIT_NUMBER,
    color=metrics.Color.CYAN,
)

metric_threads_max = metrics.Metric(
    name="threads_max",
    title=Title("Maximum number of threads"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)

perfometer_threads = perfometers.Perfometer(
    name="threads",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(700)),
    segments=["threads"],
)

graph_threads = graphs.Graph(
    name="threads",
    title=Title("Threads"),
    compound_lines=[
        "threads",
        "threads_daemon",
        "threads_max",
    ],
)
