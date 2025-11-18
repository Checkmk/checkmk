#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_nfs_read_ops = metrics.Metric(
    name="nfs_read_ops",
    title=Title("NFS read ops"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_nfs_write_ops = metrics.Metric(
    name="nfs_write_ops",
    title=Title("NFS write ops"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)

graph_nfs_ops = graphs.Bidirectional(
    name="nfs_ops",
    title=Title("NFS operations"),
    lower=graphs.Graph(
        name="nfs_ops_lower",
        title=Title("NFS operations"),
        compound_lines=["nfs_read_ops"],
    ),
    upper=graphs.Graph(
        name="nfs_ops_upper",
        title=Title("NFS operations"),
        compound_lines=["nfs_write_ops"],
    ),
)
