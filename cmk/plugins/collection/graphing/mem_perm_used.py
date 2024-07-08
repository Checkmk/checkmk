#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_mem_perm_used = metrics.Metric(
    name="mem_perm_used",
    title=Title("Permanent generation memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)

perfometer_mem_perm_used = perfometers.Perfometer(
    name="mem_perm_used",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(
            metrics.MaximumOf(
                "mem_perm_used",
                metrics.Color.GRAY,
            )
        ),
    ),
    segments=["mem_perm_used"],
)

graph_mem_perm_used = graphs.Graph(
    name="mem_perm_used",
    title=Title("Permanent generation memory"),
    minimal_range=graphs.MinimalRange(
        0,
        metrics.MaximumOf(
            "mem_perm_used",
            metrics.Color.GRAY,
        ),
    ),
    compound_lines=["mem_perm_used"],
    simple_lines=[
        metrics.WarningOf("mem_perm_used"),
        metrics.CriticalOf("mem_perm_used"),
        metrics.MaximumOf(
            "mem_perm_used",
            metrics.Color.GRAY,
        ),
    ],
)
