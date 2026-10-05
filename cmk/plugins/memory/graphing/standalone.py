#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.metrics import Color, IECNotation, Metric, StrictPrecision, Unit

UNIT_BYTES = Unit(IECNotation("B"), StrictPrecision(2))
UNIT_BYTES_AUTO_PRECISION = Unit(IECNotation("B"))

metric_percpu = Metric(
    name="percpu",
    title=Title("Memory allocated to percpu"),
    unit=UNIT_BYTES,
    color=Color.PURPLE,
)
metric_kreclaimable = Metric(
    name="kreclaimable",
    title=Title("Reclaimable kernel allocations"),
    unit=UNIT_BYTES,
    color=Color.PURPLE,
)
metric_sunreclaim = Metric(
    name="sunreclaim",
    title=Title("Unreclaimable slab"),
    unit=UNIT_BYTES,
    color=Color.PURPLE,
)
metric_swap_free = Metric(
    name="swap_free",
    title=Title("Free swap space"),
    unit=UNIT_BYTES_AUTO_PRECISION,
    color=Color.LIGHT_BLUE,
)
metric_mem_lnx_pending = Metric(
    name="mem_lnx_pending",
    title=Title("Pending memory"),
    unit=UNIT_BYTES_AUTO_PRECISION,
    color=Color.YELLOW,
)
metric_mem_lnx_unevictable = Metric(
    name="mem_lnx_unevictable",
    title=Title("Unevictable memory"),
    unit=UNIT_BYTES_AUTO_PRECISION,
    color=Color.GREEN,
)
metric_mem_lnx_anon_pages = Metric(
    name="mem_lnx_anon_pages",
    title=Title("Anonymous pages"),
    unit=UNIT_BYTES_AUTO_PRECISION,
    color=Color.DARK_ORANGE,
)
metric_mem_lnx_shmem = Metric(
    name="mem_lnx_shmem",
    title=Title("Shared memory"),
    unit=UNIT_BYTES_AUTO_PRECISION,
    color=Color.DARK_YELLOW,
)
metric_mem_lnx_mapped = Metric(
    name="mem_lnx_mapped",
    title=Title("Mapped data"),
    unit=UNIT_BYTES_AUTO_PRECISION,
    color=Color.GRAY,
)
metric_mem_lnx_anon_huge_pages = Metric(
    name="mem_lnx_anon_huge_pages",
    title=Title("Anonymous huge pages"),
    unit=UNIT_BYTES_AUTO_PRECISION,
    color=Color.LIGHT_BLUE,
)
metric_mem_lnx_hardware_corrupted = Metric(
    name="mem_lnx_hardware_corrupted",
    title=Title("Hardware corrupted memory"),
    unit=UNIT_BYTES_AUTO_PRECISION,
    color=Color.DARK_PINK,
)
