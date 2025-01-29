#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PARTS_PER_MILLION = metrics.Unit(metrics.DecimalNotation("ppm"))

metric_parts_per_million = metrics.Metric(
    name="parts_per_million",
    title=Title("Parts per Million"),
    unit=UNIT_PARTS_PER_MILLION,
    color=metrics.Color.DARK_BLUE,
)

perfometer_parts_per_million = perfometers.Perfometer(
    name="parts_per_million",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(90),
    ),
    segments=["parts_per_million"],
)
