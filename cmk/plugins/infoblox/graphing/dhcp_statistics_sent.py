#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_dhcp_acks = metrics.Metric(
    name="dhcp_acks",
    title=Title("DHCP sent acks"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_dhcp_nacks = metrics.Metric(
    name="dhcp_nacks",
    title=Title("DHCP sent nacks"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_dhcp_offers = metrics.Metric(
    name="dhcp_offers",
    title=Title("DHCP sent offers"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

graph_dhcp_statistics_sent = graphs.Graph(
    name="dhcp_statistics_sent",
    title=Title("DHCP statistics (sent messages)"),
    compound_lines=[
        "dhcp_offers",
        "dhcp_acks",
        "dhcp_nacks",
    ],
)
