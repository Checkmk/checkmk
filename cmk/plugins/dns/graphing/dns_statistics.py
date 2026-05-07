#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_dns_failures = metrics.Metric(
    name="dns_failures",
    title=Title("DNS failed queries"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_dns_nxdomain = metrics.Metric(
    name="dns_nxdomain",
    title=Title("DNS queries received for non-existent domain"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GRAY,
)
metric_dns_nxrrset = metrics.Metric(
    name="dns_nxrrset",
    title=Title("DNS queries received for non-existent record"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_dns_recursion = metrics.Metric(
    name="dns_recursion",
    title=Title("DNS queries received using recursion"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BROWN,
)
metric_dns_referrals = metrics.Metric(
    name="dns_referrals",
    title=Title("DNS referrals"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_dns_successes = metrics.Metric(
    name="dns_successes",
    title=Title("DNS successful responses"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

graph_dns_statistics = graphs.Graph(
    name="dns_statistics",
    title=Title("DNS statistics"),
    compound_lines=[
        "dns_successes",
        "dns_referrals",
        "dns_recursion",
        "dns_failures",
        "dns_nxrrset",
        "dns_nxdomain",
    ],
)
