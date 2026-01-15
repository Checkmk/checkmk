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
    title=Title("Slab (Various smaller caches)"),
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
metric_sreclaimable = Metric(
    name="sreclaimable",
    title=Title("Reclaimable slab"),
    unit=UNIT_BYTES,
    color=Color.ORANGE,
)

perfometer_mem_used_perc = Perfometer(
    name="mem_used_perc",
    focus_range=FocusRange(
        Closed(0),
        Closed(100.0),
    ),
    segments=[
        Fraction(
            Title(""),
            UNIT_PERCENTAGE,
            Color.BLUE,
            dividend=Product(
                Title(""),
                UNIT_NUMBER,
                Color.GRAY,
                [
                    Constant(
                        Title(""),
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
    title=Title("RAM (Cached, buffers)"),
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
    title=Title("RAM (Total, cached, buffers)"),
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
            Title(""),
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
    title=Title("RAM + swap overview"),
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
        "swap_cached",
    ],
    simple_lines=["swap_total"],
)
graph_caches = Graph(
    name="caches",
    title=Title("Caches"),
    compound_lines=[
        "mem_lnx_slab",
        "swap_cached",
        "mem_lnx_buffers",
        "mem_lnx_cached",
    ],
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
