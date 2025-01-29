#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_dhcp_declines = metrics.Metric(
    name="dhcp_declines",
    title=Title("DHCP received declines"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_dhcp_discovery = metrics.Metric(
    name="dhcp_discovery",
    title=Title("DHCP Discovery messages"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_dhcp_informs = metrics.Metric(
    name="dhcp_informs",
    title=Title("DHCP received informs"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BROWN,
)
metric_dhcp_others = metrics.Metric(
    name="dhcp_others",
    title=Title("DHCP received other messages"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_dhcp_releases = metrics.Metric(
    name="dhcp_releases",
    title=Title("DHCP received releases"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_dhcp_requests = metrics.Metric(
    name="dhcp_requests",
    title=Title("DHCP received requests"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GRAY,
)

graph_dhcp_statistics_received = graphs.Graph(
    name="dhcp_statistics_received",
    title=Title("DHCP statistics (received messages)"),
    compound_lines=[
        "dhcp_discovery",
        "dhcp_requests",
        "dhcp_releases",
        "dhcp_declines",
        "dhcp_informs",
        "dhcp_others",
    ],
)
