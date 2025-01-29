#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))

metric_publish_bytes_sent_rate = metrics.Metric(
    name="publish_bytes_sent_rate",
    title=Title("PUBLISH messages: Bytes sent"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_publish_bytes_received_rate = metrics.Metric(
    name="publish_bytes_received_rate",
    title=Title("PUBLISH messages: Bytes received"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.GREEN,
)

graph_publish_bytes_transmitted = graphs.Bidirectional(
    name="publish_bytes_transmitted",
    title=Title("PUBLISH messages: Bytes sent/received"),
    lower=graphs.Graph(
        name="publish_bytes_transmitted",
        title=Title("PUBLISH messages: Bytes sent/received"),
        compound_lines=["publish_bytes_sent_rate"],
    ),
    upper=graphs.Graph(
        name="publish_bytes_transmitted",
        title=Title("PUBLISH messages: Bytes sent/received"),
        compound_lines=["publish_bytes_received_rate"],
    ),
)
