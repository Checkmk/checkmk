#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_licenses = metrics.Metric(
    name="licenses",
    title=Title("Used licenses"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_licenses_total = metrics.Metric(
    name="licenses_total",
    title=Title("Total licenses"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

perfometer_licenses = perfometers.Perfometer(
    name="licenses",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(900),
    ),
    segments=["licenses"],
)

graph_licenses_total = graphs.Graph(
    name="licenses_total",
    title=Title("Licenses"),
    compound_lines=[
        "licenses_total",
        "licenses",
    ],
)
graph_licenses_max = graphs.Graph(
    name="licenses_max",
    title=Title("Licenses"),
    minimal_range=graphs.MinimalRange(
        0,
        metrics.MaximumOf(
            "licenses",
            metrics.Color.GRAY,
        ),
    ),
    compound_lines=["licenses"],
    simple_lines=[
        metrics.WarningOf("licenses"),
        metrics.CriticalOf("licenses"),
        metrics.MaximumOf(
            "licenses",
            metrics.Color.GRAY,
        ),
    ],
)
