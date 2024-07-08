#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_threads_busy = metrics.Metric(
    name="threads_busy",
    title=Title("Busy threads"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_threads_idle = metrics.Metric(
    name="threads_idle",
    title=Title("Idle threads"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)

perfometer_threads_busy_threads_idle = perfometers.Stacked(
    name="threads_busy_threads_idle",
    lower=perfometers.Perfometer(
        name="threads_busy",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(
                metrics.MaximumOf(
                    "threads_busy",
                    metrics.Color.GRAY,
                )
            ),
        ),
        segments=["threads_busy"],
    ),
    upper=perfometers.Perfometer(
        name="threads_idle",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(
                metrics.MaximumOf(
                    "threads_idle",
                    metrics.Color.GRAY,
                )
            ),
        ),
        segments=["threads_idle"],
    ),
)

graph_threadpool = graphs.Graph(
    name="threadpool",
    title=Title("Threadpool"),
    compound_lines=[
        "threads_busy",
        "threads_idle",
    ],
)
