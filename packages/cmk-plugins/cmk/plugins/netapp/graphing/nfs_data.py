#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_nfs_read_data = metrics.Metric(
    name="nfs_read_data",
    title=Title("NFS data read"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_nfs_write_data = metrics.Metric(
    name="nfs_write_data",
    title=Title("NFS data written"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)

graph_nfs_traffic = graphs.Bidirectional(
    name="nfs_traffic",
    title=Title("NFS traffic"),
    lower=graphs.Graph(
        name="nfs_traffic_lower",
        title=Title("NFS traffic"),
        compound_lines=["nfs_read_data"],
    ),
    upper=graphs.Graph(
        name="nfs_traffic_upper",
        title=Title("NFS traffic"),
        compound_lines=["nfs_write_data"],
    ),
)
