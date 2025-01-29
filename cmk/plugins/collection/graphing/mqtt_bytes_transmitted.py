#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))

metric_bytes_sent_rate = metrics.Metric(
    name="bytes_sent_rate",
    title=Title("Bytes sent"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_bytes_received_rate = metrics.Metric(
    name="bytes_received_rate",
    title=Title("Bytes received"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.GREEN,
)

graph_bytes_transmitted = graphs.Bidirectional(
    name="bytes_transmitted",
    title=Title("Bytes sent/received"),
    lower=graphs.Graph(
        name="bytes_transmitted",
        title=Title("Bytes sent/received"),
        compound_lines=["bytes_sent_rate"],
    ),
    upper=graphs.Graph(
        name="bytes_transmitted",
        title=Title("Bytes sent/received"),
        compound_lines=["bytes_received_rate"],
    ),
)
