#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

metric_meraki_last_reported = metrics.Metric(
    name="last_reported",
    title=Title("Last reported"),
    unit=metrics.Unit(metrics.TimeNotation()),
    color=metrics.Color.LIGHT_GREEN,
)

graph_meraki_device_status = graphs.Graph(
    name="meraki_device_status",
    title=Title("Last reported"),
    compound_lines=["last_reported"],
    simple_lines=[
        metrics.WarningOf("last_reported"),
        metrics.CriticalOf("last_reported"),
    ],
)

perfometer_meraki_last_reported = perfometers.Perfometer(
    name="meraki_last_reported",
    focus_range=perfometers.FocusRange(lower=perfometers.Closed(0), upper=perfometers.Open(7200)),
    segments=["last_reported"],
)
