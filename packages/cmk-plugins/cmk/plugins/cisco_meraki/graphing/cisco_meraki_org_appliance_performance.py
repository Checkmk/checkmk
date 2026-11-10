#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

metric_utilization = metrics.Metric(
    name="utilization",
    title=Title("Performance utilization"),
    unit=metrics.Unit(metrics.DecimalNotation("%")),
    color=metrics.Color.LIGHT_GREEN,
)

graph_cisco_meraki_appliance_utilization = graphs.Graph(
    name="cisco_meraki_appliance_utilization",
    title=Title("Appliance device utilization"),
    compound_lines=["utilization"],
    simple_lines=[
        metrics.WarningOf("utilization"),
        metrics.CriticalOf("utilization"),
    ],
    minimal_range=graphs.MinimalRange(0, 100),
)

perfometer_utilization = perfometers.Perfometer(
    name="utilization",
    segments=["utilization"],
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100)),
)
