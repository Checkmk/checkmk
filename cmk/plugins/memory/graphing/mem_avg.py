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

UNIT_BYTES = Unit(IECNotation("B"), StrictPrecision(2))

metric_mem_used_avg = Metric(
    name="mem_used_avg",
    title=Title("RAM used (averaged)"),
    unit=UNIT_BYTES,
    color=Color.LIGHT_PURPLE,
)
metric_mem_free_avg = Metric(
    name="mem_free_avg",
    title=Title("RAM free (averaged)"),
    unit=UNIT_BYTES,
    color=Color.LIGHT_GREEN,
)

graph_mem_absolute_avg = Graph(
    name="mem_absolute_avg",
    title=Title("RAM (averaged)"),
    simple_lines=(
        Sum(Title("Total RAM"), Color.DARK_BLUE, ("mem_used_avg", "mem_free_avg")),
        WarningOf("mem_used_avg"),
        CriticalOf("mem_used_avg"),
    ),
    compound_lines=(
        "mem_used_avg",
        "mem_free_avg",
    ),
)
