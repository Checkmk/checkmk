#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_cmk_hosts_up = metrics.Metric(
    name="cmk_hosts_up",
    title=Title("UP hosts"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_CYAN,
)
metric_cmk_hosts_down = metrics.Metric(
    name="cmk_hosts_down",
    title=Title("DOWN hosts"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)
metric_cmk_hosts_unreachable = metrics.Metric(
    name="cmk_hosts_unreachable",
    title=Title("Unreachable hosts"),
    unit=UNIT_NUMBER,
    color=metrics.Color.ORANGE,
)
metric_cmk_hosts_in_downtime = metrics.Metric(
    name="cmk_hosts_in_downtime",
    title=Title("Hosts in downtime"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
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
