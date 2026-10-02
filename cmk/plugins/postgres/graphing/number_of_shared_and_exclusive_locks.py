#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_exclusive_locks = metrics.Metric(
    name="exclusive_locks",
    title=Title("Exclusive locks"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_shared_locks = metrics.Metric(
    name="shared_locks",
    title=Title("Shared locks"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)

graph_number_of_shared_and_exclusive_locks = graphs.Graph(
    name="number_of_shared_and_exclusive_locks",
    title=Title("Number of shared and exclusive locks"),
    compound_lines=[
        "shared_locks",
        "exclusive_locks",
    ],
)
