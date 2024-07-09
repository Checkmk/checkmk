#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_last_updated = metrics.Metric(
    name="last_updated",
    title=Title("Last Updated"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)

perfometer_last_updated = perfometers.Perfometer(
    name="last_updated",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(70)),
    segments=["last_updated"],
)
