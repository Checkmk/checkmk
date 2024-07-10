#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import (
    Color,
    CriticalOf,
    IECNotation,
    Metric,
    StrictPrecision,
    Sum,
    Unit,
    WarningOf,
)
from cmk.graphing.v1.perfometers import Closed, FocusRange, Perfometer

UNIT_BYTES = Unit(IECNotation("B"), StrictPrecision(2))

metric_mem_used = Metric(
    name="mem_used",
    title=Title("RAM used"),
    unit=UNIT_BYTES,
    color=Color.PURPLE,
)
metric_mem_free = Metric(
    name="mem_free",
    title=Title("RAM free"),
    unit=UNIT_BYTES,
    color=Color.GREEN,
)
metric_mem_total = Metric(
    name="mem_total",
    title=Title("RAM installed"),
    unit=UNIT_BYTES,
    color=Color.BLUE,
)

perfometer_mem_used = Perfometer(
    name="mem_used",
    focus_range=FocusRange(Closed(0), Closed("mem_total")),
    segments=["mem_used"],
)

graph_mem_absolute = Graph(
    name="mem_absolute",
    title=Title("RAM"),
    simple_lines=(
        Sum(Title("Total RAM"), Color.DARK_BLUE, ("mem_used", "mem_free")),
        WarningOf("mem_used"),
        CriticalOf("mem_used"),
    ),
    compound_lines=(
        "mem_used",
        "mem_free",
    ),
)
