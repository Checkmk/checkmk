#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_normal_updates = metrics.Metric(
    name="normal_updates",
    title=Title("Pending normal updates"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_security_updates = metrics.Metric(
    name="security_updates",
    title=Title("Pending security updates"),
    unit=UNIT_COUNTER,
    color=metrics.Color.RED,
)

perfometer_security_updates_normal_updates = perfometers.Stacked(
    name="security_updates_normal_updates",
    lower=perfometers.Perfometer(
        name="security_updates",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(20),
        ),
        segments=["security_updates"],
    ),
    upper=perfometers.Perfometer(
        name="normal_updates",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(20),
        ),
        segments=["normal_updates"],
    ),
)

graph_pending_updates = graphs.Graph(
    name="pending_updates",
    title=Title("Pending updates"),
    compound_lines=[
        "normal_updates",
        "security_updates",
    ],
)
