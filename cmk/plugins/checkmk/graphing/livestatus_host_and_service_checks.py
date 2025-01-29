#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_host_check_rate = metrics.Metric(
    name="host_check_rate",
    title=Title("Host check rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_service_check_rate = metrics.Metric(
    name="service_check_rate",
    title=Title("Service check rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)

perfometer_service_check_rate_host_check_rate = perfometers.Stacked(
    name="service_check_rate_host_check_rate",
    lower=perfometers.Perfometer(
        name="service_check_rate",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(400)),
        segments=["service_check_rate"],
    ),
    upper=perfometers.Perfometer(
        name="host_check_rate",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(90)),
        segments=["host_check_rate"],
    ),
)

graph_host_and_service_checks = graphs.Graph(
    name="host_and_service_checks",
    title=Title("Host and service checks"),
    simple_lines=[
        "host_check_rate",
        "service_check_rate",
    ],
)
