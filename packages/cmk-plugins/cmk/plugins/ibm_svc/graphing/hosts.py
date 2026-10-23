#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_hosts_active = metrics.Metric(
    name="hosts_active",
    title=Title("Active hosts"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_hosts_degraded = metrics.Metric(
    name="hosts_degraded",
    title=Title("Degraded hosts"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_hosts_inactive = metrics.Metric(
    name="hosts_inactive",
    title=Title("Inactive hosts"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_hosts_offline = metrics.Metric(
    name="hosts_offline",
    title=Title("Offline hosts"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_hosts_other = metrics.Metric(
    name="hosts_other",
    title=Title("Other hosts"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

graph_cluster_hosts = graphs.Graph(
    name="cluster_hosts",
    title=Title("Hosts"),
    compound_lines=[
        "hosts_active",
        "hosts_inactive",
        "hosts_degraded",
        "hosts_offline",
        "hosts_other",
    ],
    optional=["hosts_active"],
)
