#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_cifs_read_latency = metrics.Metric(
    name="cifs_read_latency",
    title=Title("CIFS read latency"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_cifs_write_latency = metrics.Metric(
    name="cifs_write_latency",
    title=Title("CIFS write latency"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)

graph_cifs_latency = graphs.Bidirectional(
    name="cifs_latency",
    title=Title("CIFS latency"),
    lower=graphs.Graph(
        name="cifs_latency_lower",
        title=Title("CIFS latency"),
        compound_lines=["cifs_read_latency"],
    ),
    upper=graphs.Graph(
        name="cifs_latency_upper",
        title=Title("CIFS latency"),
        compound_lines=["cifs_write_latency"],
    ),
)
