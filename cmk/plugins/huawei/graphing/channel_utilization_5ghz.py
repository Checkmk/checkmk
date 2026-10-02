#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_channel_utilization_5ghz = metrics.Metric(
    name="channel_utilization_5ghz",
    title=Title("Channel utilization for 5GHz band"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)

graph_channel_utilization_5ghz = graphs.Graph(
    name="channel_utilization_5ghz",
    title=Title("Channel utilization for 5GHz band"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=["channel_utilization_5ghz"],
    simple_lines=[
        metrics.WarningOf("channel_utilization_5ghz"),
        metrics.CriticalOf("channel_utilization_5ghz"),
    ],
)
