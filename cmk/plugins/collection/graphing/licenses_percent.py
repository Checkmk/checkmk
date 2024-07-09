#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_license_percentage = metrics.Metric(
    name="license_percentage",
    title=Title("Used licenses"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)

perfometer_license_percentage = perfometers.Perfometer(
    name="license_percentage",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100.0),
    ),
    segments=["license_percentage"],
)
