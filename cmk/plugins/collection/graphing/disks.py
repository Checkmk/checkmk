#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_disks = metrics.Metric(
    name="disks",
    title=Title("Disks"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_failed_disks = metrics.Metric(
    name="failed_disks",
    title=Title("Failed disk"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_spare_disks = metrics.Metric(
    name="spare_disks",
    title=Title("Spare disk"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)

graph_spare_and_broken_disks = graphs.Graph(
    name="spare_and_broken_disks",
    title=Title("Spare and broken disks"),
    compound_lines=[
        "disks",
        "spare_disks",
        "failed_disks",
    ],
)
