#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_mem_esx_private = metrics.Metric(
    name="mem_esx_private",
    title=Title("Private memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_mem_esx_shared = metrics.Metric(
    name="mem_esx_shared",
    title=Title("Shared memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)

graph_private_and_shared_memory = graphs.Graph(
    name="private_and_shared_memory",
    title=Title("Private and shared memory"),
    compound_lines=[
        "mem_esx_shared",
        "mem_esx_private",
    ],
)
