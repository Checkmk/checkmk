#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_deadlocks = metrics.Metric(
    name="deadlocks",
    title=Title("Deadlocks"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
metric_lockwaits = metrics.Metric(
    name="lockwaits",
    title=Title("Waitlocks"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLACK,
)

perfometer_deadlocks_lockwaits = perfometers.Bidirectional(
    name="deadlocks_lockwaits",
    left=perfometers.Perfometer(
        name="deadlocks",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(90),
        ),
        segments=["deadlocks"],
    ),
    right=perfometers.Perfometer(
        name="lockwaits",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(90),
        ),
        segments=["lockwaits"],
    ),
)

graph_deadlocks_and_waits = graphs.Graph(
    name="deadlocks_and_waits",
    title=Title("Dead- and waitlocks"),
    compound_lines=[
        "deadlocks",
        "lockwaits",
    ],
)
