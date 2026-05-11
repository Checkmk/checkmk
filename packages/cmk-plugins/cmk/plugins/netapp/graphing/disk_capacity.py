#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_disk_capacity = metrics.Metric(
    name="disk_capacity",
    title=Title("Total disk capacity"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)

perfometer_disk_capacity = perfometers.Perfometer(
    name="disk_capacity",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(50000000000000),
    ),
    segments=["disk_capacity"],
)
