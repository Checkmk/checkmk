#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_DECIBEL_MILLIVOLTS = metrics.Unit(metrics.DecimalNotation("dBmV"))

metric_downstream_power = metrics.Metric(
    name="downstream_power",
    title=Title("Downstream power"),
    unit=UNIT_DECIBEL_MILLIVOLTS,
    color=metrics.Color.ORANGE,
)

perfometer_downstream_power = perfometers.Perfometer(
    name="downstream_power",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(100)),
    segments=["downstream_power"],
)
