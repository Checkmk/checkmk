#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"), metrics.StrictPrecision(2))

metric_zswap = metrics.Metric(
    name="zswap",
    title=Title("Zswap memory (compressed size)"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_zswapped = metrics.Metric(
    name="zswapped",
    title=Title("Memory stored in zswap (original size)"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_GREEN,
)

# Zswap is the RAM holding Zswapped, so the two are not stacked.
graph_zswap = graphs.Graph(
    name="zswap",
    title=Title("Zswap"),
    simple_lines=[
        "zswapped",
        "zswap",
    ],
)
