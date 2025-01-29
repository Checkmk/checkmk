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

metric_pagefile_used_avg = Metric(
    name="pagefile_used_avg",
    title=Title("Used virtual memory (averaged)"),
    unit=UNIT_BYTES,
    color=Color.LIGHT_PURPLE,
)
metric_pagefile_free_avg = Metric(
    name="pagefile_free_avg",
    title=Title("Free virtual memory (averaged)"),
    unit=UNIT_BYTES,
    color=Color.LIGHT_GREEN,
)

graph_pagefile_absolute_avg = Graph(
    name="pagefile_absolute_avg",
    title=Title("Commit charge (averaged)"),
    simple_lines=(
        Sum(
            Title("Total commitable memory"),
            Color.DARK_BLUE,
            ("pagefile_used_avg", "pagefile_free_avg"),
        ),
        WarningOf("pagefile_used_avg"),
        CriticalOf("pagefile_used_avg"),
    ),
    compound_lines=(
        "pagefile_used_avg",
        "pagefile_free_avg",
    ),
)
