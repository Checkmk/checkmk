#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph, MinimalRange
from cmk.graphing.v1.metrics import Color, CriticalOf, DecimalNotation, Metric, Unit, WarningOf
from cmk.graphing.v1.perfometers import Closed, FocusRange, Perfometer

UNIT_PERCENTAGE = Unit(DecimalNotation("%"))

metric_mem_used_percent = Metric(
    name="mem_used_percent",
    title=Title("RAM usage"),
    unit=UNIT_PERCENTAGE,
    color=Color.BLUE,
)
metric_mem_used_percent_avg = Metric(
    name="mem_used_percent_avg",
    title=Title("RAM usage (averaged)"),
    unit=UNIT_PERCENTAGE,
    color=Color.PINK,
)

perfometer_mem_used_percent = Perfometer(
    name="mem_used_percent",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=("mem_used_percent",),
)

graph_mem_percent = Graph(
    name="mem_percent",
    title=Title("RAM usage"),
    minimal_range=MinimalRange(0, 100),
    simple_lines=(
        "mem_used_percent",
        WarningOf("mem_used_percent"),
        CriticalOf("mem_used_percent"),
        "mem_used_percent_avg",
        WarningOf("mem_used_percent_avg"),
        CriticalOf("mem_used_percent_avg"),
    ),
    optional=["mem_used_percent_avg"],
)
