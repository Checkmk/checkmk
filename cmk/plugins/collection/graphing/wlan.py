#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_wlan_physical_errors = metrics.Metric(
    name="wlan_physical_errors",
    title=Title("WLAN physical errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_wlan_resets = metrics.Metric(
    name="wlan_resets",
    title=Title("WLAN reset operations"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_wlan_retries = metrics.Metric(
    name="wlan_retries",
    title=Title("WLAN transmission retries"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)

graph_wlan_errors = graphs.Graph(
    name="wlan_errors",
    title=Title("WLAN errors, reset operations and transmission retries"),
    compound_lines=[
        "wlan_physical_errors",
        "wlan_resets",
        "wlan_retries",
    ],
)
