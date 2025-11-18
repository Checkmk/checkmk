#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_san_read_ops = metrics.Metric(
    name="san_read_ops",
    title=Title("SAN read ops"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_san_write_ops = metrics.Metric(
    name="san_write_ops",
    title=Title("SAN write ops"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)

graph_san_ops = graphs.Bidirectional(
    name="san_ops",
    title=Title("SAN operations"),
    lower=graphs.Graph(
        name="san_ops_lower",
        title=Title("SAN operations"),
        compound_lines=["san_read_ops"],
    ),
    upper=graphs.Graph(
        name="san_ops_upper",
        title=Title("SAN operations"),
        compound_lines=["san_write_ops"],
    ),
)
