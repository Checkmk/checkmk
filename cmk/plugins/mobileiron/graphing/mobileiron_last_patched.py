#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_mobileiron_last_patched = metrics.Metric(
    name="mobileiron_last_patched",
    title=Title("Age of security patch"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_GRAY,
)

perfometer_mobileiron_last_patched = perfometers.Perfometer(
    name="mobileiron_last_patched",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(80),
    ),
    segments=["mobileiron_last_patched"],
)
