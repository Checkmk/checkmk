#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph, MinimalRange
from cmk.graphing.v1.metrics import (
    Color,
    Constant,
    CriticalOf,
    DecimalNotation,
    Fraction,
    IECNotation,
    MaximumOf,
    Metric,
    Product,
    StrictPrecision,
    Sum,
    Unit,
    WarningOf,
)
from cmk.graphing.v1.perfometers import Closed, FocusRange, Open, Perfometer

UNIT_BYTES = Unit(IECNotation("B"), StrictPrecision(2))
UNIT_NUMBER = Unit(DecimalNotation(""))
UNIT_PERCENTAGE = Unit(DecimalNotation("%"))

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
    title=Title("Total usable RAM"),
    unit=UNIT_BYTES,
    color=Color.BLUE,
)
metric_swap_total = Metric(
    name="swap_total",
    title=Title("Swap installed"),
    unit=UNIT_BYTES,
    color=Color.LIGHT_PINK,
)
metric_swap_used = Metric(
    name="swap_used",
    title=Title("Swap used"),
    unit=UNIT_BYTES,
    color=Color.DARK_GREEN,
)
metric_swap_cached = Metric(
    name="swap_cached",
    title=Title("Swap cached"),
    unit=UNIT_BYTES,
    color=Color.PINK,
)
metric_mem_lnx_slab = Metric(
    name="mem_lnx_slab",
    title=Title("Slab (various smaller caches)"),
    unit=UNIT_BYTES,
    color=Color.LIGHT_PURPLE,
)
metric_mem_lnx_cached = Metric(
    name="mem_lnx_cached",
    title=Title("Cached memory"),
    unit=UNIT_BYTES,
    color=Color.DARK_CYAN,
)
metric_mem_lnx_buffers = Metric(
    name="mem_lnx_buffers",
    title=Title("Buffered memory"),
    unit=UNIT_BYTES,
    color=Color.LIGHT_CYAN,
)
metric_swap_free = Metric(
    name="swap_free",
    title=Title("Free swap space"),
    unit=UNIT_BYTES,
    color=Color.LIGHT_BLUE,
)
metric_caches = Metric(
    name="caches",
    title=Title("Memory used by caches"),
    unit=UNIT_BYTES,
    color=Color.DARK_GRAY,
)
metric_sreclaimable = Metric(
    name="sreclaimable",
    title=Title("Reclaimable slab"),
    unit=UNIT_BYTES,
    color=Color.ORANGE,
)
metric_mem_lnx_kernel_stack = Metric(
    name="mem_lnx_kernel_stack",
    title=Title("Kernel stack"),
    unit=UNIT_BYTES,
    color=Color.PURPLE,
)
metric_mem_lnx_mlocked = Metric(
    name="mem_lnx_mlocked",
    title=Title("Locked mmap() data"),
    unit=UNIT_BYTES,
    color=Color.BLUE,
)
metric_mem_lnx_page_tables = Metric(
    name="mem_lnx_page_tables",
    title=Title("Page tables"),
    unit=UNIT_BYTES,
    color=Color.GREEN,
)
metric_sec_page_tables = Metric(
    name="sec_page_tables",
    title=Title("Secondary page tables"),
    unit=UNIT_BYTES,
    color=Color.LIGHT_GREEN,
)
metric_percpu = Metric(
    name="percpu",
    title=Title("Memory allocated to percpu"),
    unit=UNIT_BYTES,
    color=Color.LIGHT_PURPLE,
)
metric_sunreclaim = Metric(
    name="sunreclaim",
    title=Title("Unreclaimable slab"),
    unit=UNIT_BYTES,
    color=Color.BROWN,
)

perfometer_mem_used_perc = Perfometer(
    name="mem_used_perc",
    focus_range=FocusRange(
        Closed(0),
        Closed(100.0),
    ),
    segments=[
        Fraction(
            Title("Used memory percentage"),
            UNIT_PERCENTAGE,
            Color.BLUE,
            dividend=Product(
                Title("Used memory times 100"),
                UNIT_NUMBER,
                Color.GRAY,
                [
                    Constant(
                        Title("Percent factor"),
                        UNIT_NUMBER,
                        Color.GRAY,
                        100.0,
                    ),
                    "mem_used",
                ],
            ),
            divisor=MaximumOf(
                "mem_used",
                Color.GRAY,
            ),
        )
    ],
)
perfometer_mem_used_with_dynamic_range = Perfometer(
    name="mem_used_with_dynamic_range",
    focus_range=FocusRange(Closed(0), Closed("mem_total")),
    segments=["mem_used"],
)
perfometer_mem_used = Perfometer(
    name="mem_used",
    focus_range=FocusRange(Closed(0), Open(2000000000)),
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
    conflicting=("mem_lnx_cached", "mem_lnx_buffers"),
)
graph_mem_absolute_2 = Graph(
    name="mem_absolute_2",
    title=Title("RAM (cached, buffers)"),
    simple_lines=(
        # see mem_linux.py
        Sum(
            Title("Total RAM"),
            Color.DARK_BLUE,
            (
                "mem_used",
                "mem_free",
                "mem_lnx_cached",
                "mem_lnx_buffers",
                "swap_cached",
                "sreclaimable",
            ),
        ),
        WarningOf("mem_used"),
        CriticalOf("mem_used"),
    ),
    compound_lines=(
        "mem_used",
        "mem_free",
        "sreclaimable",
        "mem_lnx_cached",
        "mem_lnx_buffers",
        "swap_cached",
    ),
    optional=("swap_cached", "sreclaimable"),
    conflicting=("mem_total",),
)
graph_mem_absolute_3 = Graph(
    name="mem_absolute_3",
    title=Title("RAM (total, cached, buffers)"),
    simple_lines=(
        # see mem_linux.py
        "mem_total",
        WarningOf("mem_used"),
        CriticalOf("mem_used"),
    ),
    compound_lines=(
        "mem_used",
        "mem_free",
        "sreclaimable",
        "mem_lnx_cached",
        "mem_lnx_buffers",
        "swap_cached",
    ),
    optional=("swap_cached", "sreclaimable"),
)
graph_ram_swap_used = Graph(
    name="ram_swap_used",
    title=Title("RAM + Swap used"),
    minimal_range=MinimalRange(
        0,
        Sum(
            Title("Maximum RAM and swap used"),
            Color.GRAY,
            [
                MaximumOf(
                    "swap_used",
                    Color.GRAY,
                ),
                MaximumOf(
                    "mem_used",
                    Color.GRAY,
                ),
            ],
        ),
    ),
    compound_lines=[
        "mem_used",
        "swap_used",
    ],
    simple_lines=[
        Sum(
            Title("Total RAM + Swap installed"),
            Color.DARK_CYAN,
            [
                MaximumOf(
                    "swap_used",
                    Color.GRAY,
                ),
                MaximumOf(
                    "mem_used",
                    Color.GRAY,
                ),
            ],
        ),
        MaximumOf(
            "mem_used",
            Color.GRAY,
        ),
    ],
    conflicting=["swap_total"],
)
graph_ram_swap_overview = Graph(
    name="ram_swap_overview",
    title=Title("Total virtual memory"),
    compound_lines=[
        Sum(
            Title("RAM + swap installed"),
            Color.LIGHT_BLUE,
            [
                "mem_total",
                "swap_total",
            ],
        )
    ],
    simple_lines=[
        Sum(
            Title("RAM + swap used"),
            Color.GREEN,
            [
                "mem_used",
                "swap_used",
            ],
        )
    ],
)
graph_swap = Graph(
    name="swap",
    title=Title("Swap"),
    compound_lines=[
        "swap_used",
        "swap_free",
    ],
    # Swap cached pages still occupy their swap slot, so they are part of swap used
    simple_lines=[
        "swap_total",
        "swap_cached",
    ],
    optional=["swap_free"],
)
graph_caches = Graph(
    name="caches",
    title=Title("Caches"),
    # Only the reclaimable slab is a cache, see mem_linux.py
    compound_lines=[
        "sreclaimable",
        "swap_cached",
        "mem_lnx_buffers",
        "mem_lnx_cached",
    ],
    simple_lines=["caches"],
    optional=["caches"],
)
graph_ram_used = Graph(
    name="ram_used",
    title=Title("RAM used"),
    minimal_range=MinimalRange(
        0,
        MaximumOf(
            "mem_used",
            Color.GRAY,
        ),
    ),
    compound_lines=["mem_used"],
    simple_lines=[
        MaximumOf(
            "mem_used",
            Color.GRAY,
        ),
        WarningOf("mem_used"),
        CriticalOf("mem_used"),
    ],
    conflicting=[
        "swap_used",
        "mem_free",
    ],
)

graph_memory_that_cannot_be_swapped_out = Graph(
    name="memory_that_cannot_be_swapped_out",
    title=Title("Memory that cannot be swapped out"),
    compound_lines=[
        "mem_lnx_kernel_stack",
        "mem_lnx_page_tables",
        "mem_lnx_mlocked",
        "sec_page_tables",
        "percpu",
        "sunreclaim",
    ],
    optional=[
        "sec_page_tables",
        "percpu",
        "sunreclaim",
    ],
)

# Slab = SReclaimable + SUnreclaim
graph_slab = Graph(
    name="slab",
    title=Title("Slab"),
    compound_lines=[
        "sreclaimable",
        "sunreclaim",
    ],
    simple_lines=["mem_lnx_slab"],
)
