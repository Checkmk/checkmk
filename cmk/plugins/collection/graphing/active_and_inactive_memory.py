#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_mem_lnx_active = metrics.Metric(
    name="mem_lnx_active",
    title=Title("Active"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_mem_lnx_inactive = metrics.Metric(
    name="mem_lnx_inactive",
    title=Title("Inactive"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)

graph_active_and_inactive_memory = graphs.Graph(
    name="active_and_inactive_memory",
    title=Title("Active and inactive memory"),
    compound_lines=[
        "mem_lnx_active",
        "mem_lnx_inactive",
    ],
)
