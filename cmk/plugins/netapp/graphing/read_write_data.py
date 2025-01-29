#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_read_data = metrics.Metric(
    name="read_data",
    title=Title("Data read"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_write_data = metrics.Metric(
    name="write_data",
    title=Title("Data written"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)

graph_read_write_data = graphs.Bidirectional(
    name="read_write_data",
    title=Title("Traffic"),
    lower=graphs.Graph(
        name="read_write_data_lower",
        title=Title("Traffic"),
        compound_lines=["read_data"],
    ),
    upper=graphs.Graph(
        name="read_write_data_upper",
        title=Title("Traffic"),
        compound_lines=["write_data"],
    ),
)
