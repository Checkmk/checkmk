#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_monitored_hosts = metrics.Metric(
    name="monitored_hosts",
    title=Title("Monitored hosts"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)
metric_monitored_services = metrics.Metric(
    name="monitored_services",
    title=Title("Monitored services"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

graph_number_of_monitored_hosts_and_services = graphs.Graph(
    name="number_of_monitored_hosts_and_services",
    title=Title("Number of monitored hosts and services"),
    simple_lines=[
        "monitored_hosts",
        "monitored_services",
    ],
)
