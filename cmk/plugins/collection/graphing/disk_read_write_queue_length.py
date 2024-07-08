#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""))

metric_disk_read_ql = metrics.Metric(
    name="disk_read_ql",
    title=Title("Average disk read queue length"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)
metric_disk_write_ql = metrics.Metric(
    name="disk_write_ql",
    title=Title("Average disk write queue length"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)

graph_read_write_queue_length = graphs.Bidirectional(
    name="read_write_queue_length",
    title=Title("Read / Write queue length"),
    lower=graphs.Graph(
        name="read_write_queue_length_lower",
        title=Title("Read / Write queue length"),
        compound_lines=["disk_write_ql"],
    ),
    upper=graphs.Graph(
        name="read_write_queue_length_upper",
        title=Title("Read / Write queue length"),
        compound_lines=["disk_read_ql"],
    ),
)
