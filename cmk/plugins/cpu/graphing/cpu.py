#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import perfometers, Title
from cmk.graphing.v1.metrics import Color, Metric, TimeNotation, Unit

metric_cpu_time = Metric(
    name="cpu_time",
    title=Title("CPU Time"),
    unit=Unit(TimeNotation()),
    color=Color.BLUE,
)

perfometer_cpu_time = perfometers.Perfometer(
    name="cpu_time",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(1),
    ),
    segments=["cpu_time"],
)
