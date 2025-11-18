#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_san_read_data = metrics.Metric(
    name="san_read_data",
    title=Title("SAN data read"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_san_write_data = metrics.Metric(
    name="san_write_data",
    title=Title("SAN data written"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)

graph_san_traffic = graphs.Bidirectional(
    name="san_traffic",
    title=Title("SAN traffic"),
    lower=graphs.Graph(
        name="san_traffic_lower",
        title=Title("SAN traffic"),
        compound_lines=["san_read_data"],
    ),
    upper=graphs.Graph(
        name="san_traffic_upper",
        title=Title("SAN traffic"),
        compound_lines=["san_write_data"],
    ),
)
