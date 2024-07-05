#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_snat_usage = metrics.Metric(
    name="snat_usage",
    title=Title("SNAT usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)

perfometer_snat_usage = perfometers.Perfometer(
    name="snat_usage",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=["snat_usage"],
)
