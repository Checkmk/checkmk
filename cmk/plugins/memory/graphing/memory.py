#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph, MinimalRange
from cmk.graphing.v1.metrics import (
    Color,
    CriticalOf,
    DecimalNotation,
    IECNotation,
    Metric,
    StrictPrecision,
    Sum,
    Unit,
    WarningOf,
)
from cmk.graphing.v1.perfometers import Closed, FocusRange, Perfometer

PERCENT = Unit(DecimalNotation("%"))

BYTES = Unit(IECNotation("B"), StrictPrecision(2))

metric_file_huge_pages = Metric(
    name="file_huge_pages",
    title=Title("File huge pages"),
    unit=BYTES,
    color=Color.PURPLE,
)

metric_file_pmd_mapped = Metric(
    name="file_pmd_mapped",
    title=Title("Page cache mapped into userspace with huge pages"),
    unit=BYTES,
    color=Color.PURPLE,
)

metric_percpu = Metric(
    name="percpu",
    title=Title("Memory allocated to percpu"),
    unit=BYTES,
    color=Color.PURPLE,
)

metric_shmem_huge_pages = Metric(
    name="shmem_huge_pages",
    title=Title("Shared memory and tmpfs allocated with huge pages"),
    unit=BYTES,
    color=Color.PURPLE,
)

metric_shmem_pmd_mapped = Metric(
    name="shmem_pmd_mapped",
    title=Title("Shared memory mapped into userspace with huge pages"),
    unit=BYTES,
    color=Color.PURPLE,
)

metric_kreclaimable = Metric(
    name="kreclaimable",
    title=Title("Reclaimable kernel allocations"),
    unit=BYTES,
    color=Color.PURPLE,
)

metric_sreclaimable = Metric(
    name="sreclaimable",
    title=Title("Reclaimable slab"),
    unit=BYTES,
    color=Color.PURPLE,
)

metric_sunreclaim = Metric(
    name="sunreclaim",
    title=Title("Unreclaimable slab"),
    unit=BYTES,
    color=Color.PURPLE,
)

metric_mem_used_percent = Metric(
    name="mem_used_percent",
    title=Title("RAM used"),
    unit=PERCENT,
    color=Color.BLUE,
)

metric_mem_used_percent_avg = Metric(
    name="mem_used_percent_avg",
    title=Title("RAM used (averaged)"),
    unit=PERCENT,
    color=Color.LIGHT_BLUE,
)

metric_mem_used = Metric(
    name="mem_used",
    title=Title("RAM used"),
    unit=BYTES,
    color=Color.PURPLE,
)

metric_mem_used_avg = Metric(
    name="mem_used_avg",
    title=Title("RAM used (averaged)"),
    unit=BYTES,
    color=Color.LIGHT_PURPLE,
)

metric_mem_free = Metric(
    name="mem_free",
    title=Title("RAM free"),
    unit=BYTES,
    color=Color.GREEN,
)

metric_mem_free_avg = Metric(
    name="mem_free_avg",
    title=Title("RAM free (averaged)"),
    unit=BYTES,
    color=Color.LIGHT_GREEN,
)

metric_pagefile_used_percent = Metric(
    name="pagefile_used_percent",
    title=Title("Commit charge"),
    unit=PERCENT,
    color=Color.BLUE,
)

metric_pagefile_used_percent_avg = Metric(
    name="pagefile_used_percent_avg",
    title=Title("Commit charge (averaged)"),
    unit=PERCENT,
    color=Color.LIGHT_BLUE,
)

metric_pagefile_used = Metric(
    name="pagefile_used",
    title=Title("Commit charge"),
    unit=BYTES,
    color=Color.PURPLE,
)

metric_pagefile_used_avg = Metric(
    name="pagefile_used_avg",
    title=Title("Commit charge (averaged)"),
    unit=BYTES,
    color=Color.LIGHT_PURPLE,
)

metric_pagefile_free = Metric(
    name="pagefile_free",
    title=Title("Commitable memory"),
    unit=BYTES,
    color=Color.GREEN,
)

metric_pagefile_free_avg = Metric(
    name="pagefile_free_avg",
    title=Title("Commitable memory (averaged)"),
    unit=BYTES,
    color=Color.LIGHT_GREEN,
)

graph_mem_percent = Graph(
    name="mem_percent",
    title=Title("RAM used"),
    minimal_range=MinimalRange(0, 100),
    simple_lines=(
        "mem_used_percent",
        WarningOf("mem_used_percent"),
        CriticalOf("mem_used_percent"),
        "mem_used_percent_avg",
        WarningOf("mem_used_percent_avg"),
        CriticalOf("mem_used_percent_avg"),
    ),
)


graph_mem_absolute = Graph(
    name="mem_absolute",
    title=Title("RAM"),
    simple_lines=(
        Sum(Title("Total RAM"), Color.BLACK, ("mem_used", "mem_free")),
        WarningOf("mem_used"),
        CriticalOf("mem_used"),
    ),
    compound_lines=(
        "mem_used",
        "mem_free",
    ),
)

graph_mem_absolute_avg = Graph(
    name="mem_absolute_avg",
    title=Title("RAM (averaged)"),
    simple_lines=(
        Sum(Title("Total RAM"), Color.BLACK, ("mem_used_avg", "mem_free_avg")),
        WarningOf("mem_used_avg"),
        CriticalOf("mem_used_avg"),
    ),
    compound_lines=(
        "mem_used_avg",
        "mem_free_avg",
    ),
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


graph_pagefile_absolute = Graph(
    name="pagefile_absolute",
    title=Title("Commit charge"),
    simple_lines=(
        Sum(Title("Total commitable memory"), Color.BLACK, ("pagefile_used", "pagefile_free")),
        WarningOf("pagefile_used"),
        CriticalOf("pagefile_used"),
    ),
    compound_lines=(
        "pagefile_used",
        "pagefile_free",
    ),
)

graph_pagefile_absolute_avg = Graph(
    name="pagefile_absolute_avg",
    title=Title("Commit charge (averaged)"),
    simple_lines=(
        Sum(
            Title("Total commitable memory"),
            Color.BLACK,
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

perfometer_mem_used_percent = Perfometer(
    name="mem_used_percent",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=("mem_used_percent",),
)

perfometer_pagefile_used_percent = Perfometer(
    name="pagefile_used_percent",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=("pagefile_used_percent",),
)
