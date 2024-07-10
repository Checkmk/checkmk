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

metric_pagefile_used = Metric(
    name="pagefile_used",
    title=Title("Used virtual memory"),
    unit=UNIT_BYTES,
    color=Color.PURPLE,
)
metric_pagefile_free = Metric(
    name="pagefile_free",
    title=Title("Free virtual memory"),
    unit=UNIT_BYTES,
    color=Color.GREEN,
)

graph_pagefile_absolute = Graph(
    name="pagefile_absolute",
    title=Title("Commit charge"),
    simple_lines=(
        Sum(Title("Total commitable memory"), Color.DARK_BLUE, ("pagefile_used", "pagefile_free")),
        WarningOf("pagefile_used"),
        CriticalOf("pagefile_used"),
    ),
    compound_lines=(
        "pagefile_used",
        "pagefile_free",
    ),
)
