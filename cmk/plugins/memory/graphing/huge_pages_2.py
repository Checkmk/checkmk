#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import (
    Color,
    DecimalNotation,
    IECNotation,
    Metric,
    StrictPrecision,
    Unit,
)

UNIT_PERCENTAGE = Unit(DecimalNotation("%"))
UNIT_BYTES = Unit(IECNotation("B"), StrictPrecision(2))

metric_file_huge_pages = Metric(
    name="file_huge_pages",
    title=Title("File huge pages"),
    unit=UNIT_BYTES,
    color=Color.PURPLE,
)
metric_file_pmd_mapped = Metric(
    name="file_pmd_mapped",
    title=Title("Page cache mapped into userspace with huge pages"),
    unit=UNIT_BYTES,
    color=Color.BLUE,
)
metric_shmem_huge_pages = Metric(
    name="shmem_huge_pages",
    title=Title("Shared memory and tmpfs allocated with huge pages"),
    unit=UNIT_BYTES,
    color=Color.GREEN,
)
metric_shmem_pmd_mapped = Metric(
    name="shmem_pmd_mapped",
    title=Title("Shared memory mapped into userspace with huge pages"),
    unit=UNIT_BYTES,
    color=Color.ORANGE,
)

graph_huge_pages = Graph(
    name="huge_pages_2",
    title=Title("Huge pages"),
    simple_lines=[
        "file_huge_pages",
        "file_pmd_mapped",
        "shmem_huge_pages",
        "shmem_pmd_mapped",
    ],
)
