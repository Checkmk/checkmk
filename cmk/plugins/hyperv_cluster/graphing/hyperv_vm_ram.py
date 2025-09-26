#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, perfometers, Title
from cmk.graphing.v1.metrics import (
    Color,
    IECNotation,
    Metric,
    StrictPrecision,
    Unit,
)

BYTES_UNIT = Unit(IECNotation("B"), StrictPrecision(2))

prefix = "hyperv_ram_metrics_"

metric_hyperv_ram_assigned_ram = Metric(
    name=f"{prefix}vm_assigned_ram",
    title=Title("Current RAM"),
    unit=BYTES_UNIT,
    color=Color.PURPLE,
)

metric_hyperv_ram_start_ram = Metric(
    name=f"{prefix}vm_start_ram",
    title=Title("Start RAM"),
    unit=BYTES_UNIT,
    color=Color.LIGHT_PURPLE,
)

metric_hyperv_ram_max_ram = Metric(
    name=f"{prefix}vm_max_ram",
    title=Title("Maximum RAM"),
    unit=BYTES_UNIT,
    color=Color.DARK_BLUE,
)

metric_hyperv_ram_min_ram = Metric(
    name=f"{prefix}vm_min_ram", title=Title("Minimum RAM"), unit=BYTES_UNIT, color=Color.LIGHT_BLUE
)

metric_hyperv_ram_ram_demand = Metric(
    name=f"{prefix}vm_ram_demand",
    title=Title("Demand"),
    unit=BYTES_UNIT,
    color=Color.DARK_PURPLE,
)


def gb_to_kb(value: int) -> int:
    return value * 1024 * 1024 * 1024


perfometer_hyperv_ram_assigned_ram = perfometers.Perfometer(
    name=f"{prefix}vm_assigned_ram_perf",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(gb_to_kb(32))),
    segments=[f"{prefix}vm_assigned_ram"],
)

graph_hyperv_ram = graphs.Graph(
    name=f"{prefix}vm_ram_graph",
    title=Title("RAM Metrics"),
    compound_lines=(f"{prefix}vm_assigned_ram",),
    simple_lines=(
        f"{prefix}vm_min_ram",
        f"{prefix}vm_max_ram",
        f"{prefix}vm_start_ram",
        f"{prefix}vm_ram_demand",
    ),
    optional=(f"{prefix}vm_ram_demand",),
)
