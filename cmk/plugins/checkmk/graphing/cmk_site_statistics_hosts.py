#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

# The main dashboard shows the metrics defined here right next to host stats dashlet (in the total
# host problems graphs). Therefore, we should keep the colors in sync.

metric_cmk_hosts_up = metrics.Metric(
    name="cmk_hosts_up",
    title=Title("Up hosts"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_CYAN,
)
metric_cmk_hosts_down = metrics.Metric(
    name="cmk_hosts_down",
    title=Title("Down hosts"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,  # CSS counterpart: $hexagon-critical-color
)
metric_cmk_hosts_unreachable = metrics.Metric(
    name="cmk_hosts_unreachable",
    title=Title("Unreachable hosts"),
    unit=UNIT_NUMBER,
    color=metrics.Color.ORANGE,  # CSS counterpart: $hexagon-unknown-color
)
metric_cmk_hosts_in_downtime = metrics.Metric(
    name="cmk_hosts_in_downtime",
    title=Title("Hosts in downtime"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,  # CSS counterpart: $hexagon-downtime-color
)

graph_cmk_hosts_total = graphs.Graph(
    name="cmk_hosts_total",
    title=Title("Total number of hosts"),
    compound_lines=[
        metrics.Sum(
            Title("Total"),
            metrics.Color.BROWN,
            [
                "cmk_hosts_up",
                "cmk_hosts_unreachable",
                "cmk_hosts_in_downtime",
            ],
        )
    ],
)
graph_cmk_hosts_not_up = graphs.Graph(
    name="cmk_hosts_not_up",
    title=Title("Number of problematic hosts"),
    compound_lines=[
        "cmk_hosts_down",
        "cmk_hosts_unreachable",
        "cmk_hosts_in_downtime",
    ],
)
