#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_node_mem_allocation_ratio = metrics.Metric(
    name="node_mem_allocation_ratio",
    title=Title("Memory allocation ratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)

perfometer_mem_allocation = perfometers.Perfometer(
    name="proxmox_node_mem_allocation",
    focus_range=perfometers.FocusRange(
        lower=perfometers.Closed(0),
        upper=perfometers.Open(200),
    ),
    segments=["node_mem_allocation_ratio"],
)
