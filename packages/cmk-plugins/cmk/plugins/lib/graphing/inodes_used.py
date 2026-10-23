#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.SINotation(""), metrics.StrictPrecision(2))

metric_inodes_used = metrics.Metric(
    name="inodes_used",
    title=Title("Used inodes"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

graph_inodes_used = graphs.Graph(
    name="inodes_used",
    title=Title("Used inodes"),
    minimal_range=graphs.MinimalRange(
        0,
        metrics.MaximumOf(
            "inodes_used",
            metrics.Color.GRAY,
        ),
    ),
    compound_lines=["inodes_used"],
    simple_lines=[
        metrics.WarningOf("inodes_used"),
        metrics.CriticalOf("inodes_used"),
        metrics.MaximumOf(
            "inodes_used",
            metrics.Color.PURPLE,
        ),
    ],
)
