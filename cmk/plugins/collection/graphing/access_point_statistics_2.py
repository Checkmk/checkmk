#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_ap_devices_cleared = metrics.Metric(
    name="ap_devices_cleared",
    title=Title("Cleared"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_ap_devices_critical = metrics.Metric(
    name="ap_devices_critical",
    title=Title("Critical"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_ap_devices_minor = metrics.Metric(
    name="ap_devices_minor",
    title=Title("Minor"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

graph_access_point_statistics2 = graphs.Graph(
    name="access_point_statistics2",
    title=Title("Access point statistics"),
    compound_lines=[
        "ap_devices_cleared",
        "ap_devices_minor",
        "ap_devices_critical",
    ],
)
