#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_nfsv4_read_latency = metrics.Metric(
    name="nfsv4_read_latency",
    title=Title("NFSv4 read latency"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_nfsv4_write_latency = metrics.Metric(
    name="nfsv4_write_latency",
    title=Title("NFSv4 write latency"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)

graph_nfsv4_latency = graphs.Bidirectional(
    name="nfsv4_latency",
    title=Title("NFSv4 latency"),
    lower=graphs.Graph(
        name="nfsv4_latency_lower",
        title=Title("NFSv4 latency"),
        compound_lines=["nfsv4_read_latency"],
    ),
    upper=graphs.Graph(
        name="nfsv4_latency_upper",
        title=Title("NFSv4 latency"),
        compound_lines=["nfsv4_write_latency"],
    ),
)
