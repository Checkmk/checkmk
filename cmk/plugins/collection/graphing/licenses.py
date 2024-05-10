#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_licenses = metrics.Metric(
    name="licenses",
    title=Title("Used licenses"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_license_percentage = metrics.Metric(
    name="license_percentage",
    title=Title("Used licenses"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)
metric_licenses_total = metrics.Metric(
    name="licenses_total",
    title=Title("Total licenses"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_license_size = metrics.Metric(
    name="license_size",
    title=Title("Size of license"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_license_usage = metrics.Metric(
    name="license_usage",
    title=Title("License usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)

perfometer_licenses = perfometers.Perfometer(
    name="licenses",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(900),
    ),
    segments=["licenses"],
)
perfometer_license_percentage = perfometers.Perfometer(
    name="license_percentage",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=["license_percentage"],
)

graph_licenses = graphs.Graph(
    name="licenses_total",
    title=Title("Licenses"),
    compound_lines=[
        "licenses_total",
        "licenses",
    ],
)
graph_licenses = graphs.Graph(
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
