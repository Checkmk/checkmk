#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

metric_thread_usage = metrics.Metric(
    name="thread_usage",
    title=Title("Thread usage"),
    unit=metrics.Unit(metrics.DecimalNotation("%")),
    color=metrics.Color.YELLOW,
)

graph_thread_usage = graphs.Graph(
    name="thread_usage",
    title=Title("Thread usage"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=["thread_usage"],
    simple_lines=[
        metrics.WarningOf("thread_usage"),
        metrics.CriticalOf("thread_usage"),
    ],
)
