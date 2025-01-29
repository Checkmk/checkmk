#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_ap_devices_drifted = metrics.Metric(
    name="ap_devices_drifted",
    title=Title("Time drifted devices"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_ap_devices_not_responding = metrics.Metric(
    name="ap_devices_not_responding",
    title=Title("Not responding devices"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_ap_devices_total = metrics.Metric(
    name="ap_devices_total",
    title=Title("Total devices"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

perfometer_ap_devices_drifted_ap_devices_not_responding = perfometers.Perfometer(
    name="ap_devices_drifted_ap_devices_not_responding",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed("ap_devices_total"),
    ),
    segments=[
        "ap_devices_drifted",
        "ap_devices_not_responding",
    ],
)

graph_access_point_statistics = graphs.Graph(
    name="access_point_statistics",
    title=Title("Access point statistics"),
    compound_lines=["ap_devices_total"],
    simple_lines=[
        "ap_devices_drifted",
        "ap_devices_not_responding",
    ],
)
