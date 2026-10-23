#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"), metrics.StrictPrecision(2))

metric_mem_lnx_anon_pages = metrics.Metric(
    name="mem_lnx_anon_pages",
    title=Title("Anonymous pages"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_ORANGE,
)
metric_mem_lnx_mapped = metrics.Metric(
    name="mem_lnx_mapped",
    title=Title("Mapped data"),
    unit=UNIT_BYTES,
    color=metrics.Color.GRAY,
)
metric_mem_lnx_shmem = metrics.Metric(
    name="mem_lnx_shmem",
    title=Title("Shared memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_YELLOW,
)
metric_mem_lnx_unevictable = metrics.Metric(
    name="mem_lnx_unevictable",
    title=Title("Unevictable memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_mem_lnx_bounce = metrics.Metric(
    name="mem_lnx_bounce",
    title=Title("Bounce buffers"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_GREEN,
)

metric_kreclaimable = metrics.Metric(
    name="kreclaimable",
    title=Title("Reclaimable kernel allocations"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_BLUE,
)

# These overlap (e.g. mapped shared memory is in Mapped and Shmem), so they are not stacked.
graph_memory_types = graphs.Graph(
    name="memory_types",
    title=Title("Misc memory types"),
    simple_lines=[
        "mem_lnx_anon_pages",
        "mem_lnx_mapped",
        "mem_lnx_shmem",
        "mem_lnx_unevictable",
        "kreclaimable",
        "mem_lnx_bounce",
    ],
    optional=["kreclaimable", "mem_lnx_bounce"],
)
