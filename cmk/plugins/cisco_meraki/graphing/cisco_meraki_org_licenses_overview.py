#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

metric_remaining_time = metrics.Metric(
    name="remaining_time",
    title=Title("Remaining time"),
    unit=metrics.Unit(metrics.TimeNotation()),
    color=metrics.Color.GREEN,
)

graph_cisco_meraki_remaining_time = graphs.Graph(
    name="cisco_meraki_remaining_time",
    title=Title("Cisco Meraki licenses remaining time"),
    compound_lines=["remaining_time"],
    simple_lines=[
        metrics.WarningOf("remaining_time"),
        metrics.CriticalOf("remaining_time"),
    ],
    minimal_range=graphs.MinimalRange(0, 180),
)

perfometer_licensing = perfometers.Perfometer(
    name="meraki_remaining_time",
    focus_range=perfometers.FocusRange(perfometers.Open(0), perfometers.Open(180)),
    segments=["remaining_time"],
)
