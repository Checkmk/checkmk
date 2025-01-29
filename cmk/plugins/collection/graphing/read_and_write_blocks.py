#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_read_blocks = metrics.Metric(
    name="read_blocks",
    title=Title("Read blocks per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_write_blocks = metrics.Metric(
    name="write_blocks",
    title=Title("Write blocks per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

perfometer_read_blocks_write_blocks = perfometers.Bidirectional(
    name="read_blocks_write_blocks",
    left=perfometers.Perfometer(
        name="read_blocks",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(90000000),
        ),
        segments=["read_blocks"],
    ),
    right=perfometers.Perfometer(
        name="write_blocks",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(90000000),
        ),
        segments=["write_blocks"],
    ),
)

graph_read_and_written_blocks = graphs.Bidirectional(
    name="read_and_written_blocks",
    title=Title("Read and written blocks"),
    lower=graphs.Graph(
        name="read_and_written_blocks_lower",
        title=Title("Read and written blocks"),
        compound_lines=["write_blocks"],
    ),
    upper=graphs.Graph(
        name="read_and_written_blocks_upper",
        title=Title("Read and written blocks"),
        compound_lines=["read_blocks"],
    ),
)
