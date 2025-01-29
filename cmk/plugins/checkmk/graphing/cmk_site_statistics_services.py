#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_cmk_services_ok = metrics.Metric(
    name="cmk_services_ok",
    title=Title("OK services"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_CYAN,
)
metric_cmk_services_in_downtime = metrics.Metric(
    name="cmk_services_in_downtime",
    title=Title("Services in downtime"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)
metric_cmk_services_on_down_hosts = metrics.Metric(
    name="cmk_services_on_down_hosts",
    title=Title("Services of down hosts"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)
metric_cmk_services_warning = metrics.Metric(
    name="cmk_services_warning",
    title=Title("WARNING services"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)
metric_cmk_services_unknown = metrics.Metric(
    name="cmk_services_unknown",
    title=Title("UNKNOWN services"),
    unit=UNIT_NUMBER,
    color=metrics.Color.ORANGE,
)
metric_cmk_services_critical = metrics.Metric(
    name="cmk_services_critical",
    title=Title("CRITICAL services"),
    unit=UNIT_NUMBER,
    color=metrics.Color.RED,
)

graph_cmk_services_total = graphs.Graph(
    name="cmk_services_total",
    title=Title("Total number of services"),
    compound_lines=[
        metrics.Sum(
            Title("Total"),
            metrics.Color.BLUE,
            [
                "cmk_services_ok",
                "cmk_services_in_downtime",
                "cmk_services_on_down_hosts",
                "cmk_services_warning",
                "cmk_services_unknown",
                "cmk_services_critical",
            ],
        )
    ],
)
graph_cmk_services_not_ok = graphs.Graph(
    name="cmk_services_not_ok",
    title=Title("Number of problematic services"),
    compound_lines=[
        "cmk_services_in_downtime",
        "cmk_services_on_down_hosts",
        "cmk_services_warning",
        "cmk_services_unknown",
        "cmk_services_critical",
    ],
)
