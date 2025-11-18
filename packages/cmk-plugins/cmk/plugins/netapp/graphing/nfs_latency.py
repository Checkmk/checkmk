#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_nfs_read_latency = metrics.Metric(
    name="nfs_read_latency",
    title=Title("NFS read latency"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_nfs_write_latency = metrics.Metric(
    name="nfs_write_latency",
    title=Title("NFS write latency"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)

graph_nfs_latency = graphs.Bidirectional(
    name="nfs_latency",
    title=Title("NFS latency"),
    lower=graphs.Graph(
        name="nfs_latency_lower",
        title=Title("NFS latency"),
        compound_lines=["nfs_read_latency"],
    ),
    upper=graphs.Graph(
        name="nfs_latency_upper",
        title=Title("NFS latency"),
        compound_lines=["nfs_write_latency"],
    ),
)
