#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_availability = metrics.Metric(
    name="availability",
    title=Title("Availability"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)

perfometer_availability = perfometers.Perfometer(
    name="availability",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=["availability"],
)

graph_availability = graphs.Graph(
    name="availability",
    title=Title("Availability"),
    simple_lines=["availability"],
)
