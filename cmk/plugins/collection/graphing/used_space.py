#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_used_space = metrics.Metric(
    name="used_space",
    title=Title("Used storage space"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)

perfometer_used_space = perfometers.Perfometer(
    name="used_space",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(2000000000),
    ),
    segments=["used_space"],
)

graph_used_space = graphs.Graph(
    name="used_space",
    title=Title("Used storage space"),
    simple_lines=["used_space"],
)
