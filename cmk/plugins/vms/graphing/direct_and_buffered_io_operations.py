#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))

metric_buffered_io = metrics.Metric(
    name="buffered_io",
    title=Title("Buffered I/O"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_direct_io = metrics.Metric(
    name="direct_io",
    title=Title("Direct I/O"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)

perfometer_buffered_io_direct_io = perfometers.Stacked(
    name="buffered_io_direct_io",
    lower=perfometers.Perfometer(
        name="buffered_io",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(50),
        ),
        segments=["buffered_io"],
    ),
    upper=perfometers.Perfometer(
        name="direct_io",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(50),
        ),
        segments=["direct_io"],
    ),
)

graph_direct_and_buffered_io_operations = graphs.Graph(
    name="direct_and_buffered_io_operations",
    title=Title("Direct and buffered I/O operations"),
    compound_lines=[
        "direct_io",
        "buffered_io",
    ],
)
