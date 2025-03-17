#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_disk_average_read_request_size = metrics.Metric(
    name="disk_average_read_request_size",
    title=Title("Average read request size"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_disk_average_write_request_size = metrics.Metric(
    name="disk_average_write_request_size",
    title=Title("Average write request size"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)

graph_average_request_size = graphs.Bidirectional(
    name="average_request_size",
    title=Title("Average read and write request size"),
    lower=graphs.Graph(
        name="disk_average_write_request_size",
        title=Title("Average write request size"),
        compound_lines=["disk_average_write_request_size"],
    ),
    upper=graphs.Graph(
        name="disk_average_read_request_size",
        title=Title("Average read request size"),
        compound_lines=["disk_average_read_request_size"],
    ),
)
