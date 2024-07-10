#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph, MinimalRange
from cmk.graphing.v1.metrics import Color, CriticalOf, DecimalNotation, Metric, Unit, WarningOf
from cmk.graphing.v1.perfometers import Closed, FocusRange, Perfometer

UNIT_PERCENTAGE = Unit(DecimalNotation("%"))

metric_pagefile_used_percent = Metric(
    name="pagefile_used_percent",
    title=Title("Used virtual memory"),
    unit=UNIT_PERCENTAGE,
    color=Color.BLUE,
)
metric_pagefile_used_percent_avg = Metric(
    name="pagefile_used_percent_avg",
    title=Title("Used virtual memory (averaged)"),
    unit=UNIT_PERCENTAGE,
    color=Color.PINK,
)

perfometer_pagefile_used_percent = Perfometer(
    name="pagefile_used_percent",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=("pagefile_used_percent",),
)

graph_pagefile_percent = Graph(
    name="pagefile_percent",
    title=Title("Commit charge"),
    minimal_range=MinimalRange(0, 100),
    simple_lines=(
        "pagefile_used_percent",
        WarningOf("pagefile_used_percent"),
        CriticalOf("pagefile_used_percent"),
        "pagefile_used_percent_avg",
        WarningOf("pagefile_used_percent_avg"),
        CriticalOf("pagefile_used_percent_avg"),
    ),
)
