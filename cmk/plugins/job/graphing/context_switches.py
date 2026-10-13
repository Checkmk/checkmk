#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_invol_context_switches = metrics.Metric(
    name="invol_context_switches",
    title=Title("Involuntary context switches"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_vol_context_switches = metrics.Metric(
    name="vol_context_switches",
    title=Title("Voluntary context switches"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

graph_context_switches = graphs.Graph(
    name="context_switches",
    title=Title("Context switches"),
    compound_lines=[
        "vol_context_switches",
        "invol_context_switches",
    ],
)
