#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_snapshot_used = metrics.Metric(
    name="snapshot_reserve_used",
    title=Title("Snapshot reserve used space"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)

metric_snapshot_reserve_size = metrics.Metric(
    name="snapshot_reserve_size",
    title=Title("Snapshot reserve size"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)

graph_snapshot_reserve = graphs.Graph(
    name="snapshot_reserve",
    title=Title("Snapshot reserve"),
    compound_lines=["snapshot_reserve_used"],
    simple_lines=["snapshot_reserve_size"],
)
