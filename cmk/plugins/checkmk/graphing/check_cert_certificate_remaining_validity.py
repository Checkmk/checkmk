#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_certificate_remaining_validity = metrics.Metric(
    name="certificate_remaining_validity",
    title=Title("Remaining certificate validity time"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)

perfometer_certificate_remaining_validity = perfometers.Perfometer(
    name="certificate_remaining_validity",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(15552000),  # 180 days
    ),
    segments=["certificate_remaining_validity"],
)
