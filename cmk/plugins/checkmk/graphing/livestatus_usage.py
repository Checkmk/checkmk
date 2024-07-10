#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_livestatus_usage = metrics.Metric(
    name="livestatus_usage",
    title=Title("Livestatus usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)

graph_livestatus_usage = graphs.Graph(
    name="livestatus_usage",
    title=Title("Livestatus usage"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=["livestatus_usage"],
)
