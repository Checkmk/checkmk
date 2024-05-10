#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_citrix_load = metrics.Metric(
    name="citrix_load",
    title=Title("Citrix Load"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)

perfometer_citrix_load = perfometers.Perfometer(
    name="citrix_load",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=["citrix_load"],
)

graph_citrix_serverload = graphs.Graph(
    name="citrix_serverload",
    title=Title("Citrix Serverload"),
    minimal_range=graphs.MinimalRange(0, 100),
    compound_lines=["citrix_load"],
)
