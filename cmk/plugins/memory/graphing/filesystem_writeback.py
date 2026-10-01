#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_mem_lnx_dirty = metrics.Metric(
    name="mem_lnx_dirty",
    title=Title("Dirty disk blocks"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_mem_lnx_nfs_unstable = metrics.Metric(
    name="mem_lnx_nfs_unstable",
    title=Title("Modified NFS data"),
    unit=UNIT_BYTES,
    color=metrics.Color.BROWN,
)
metric_mem_lnx_writeback = metrics.Metric(
    name="mem_lnx_writeback",
    title=Title("Currently being written"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_mem_lnx_writeback_tmp = metrics.Metric(
    name="mem_lnx_writeback_tmp",
    title=Title("Dirty FUSE data"),
    unit=UNIT_BYTES,
    color=metrics.Color.GRAY,
)
metric_mem_lnx_pending = metrics.Metric(
    name="mem_lnx_pending",
    title=Title("Pending memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)

graph_filesystem_writeback = graphs.Graph(
    name="filesystem_writeback",
    title=Title("File system writeback"),
    compound_lines=[
        "mem_lnx_dirty",
        "mem_lnx_writeback",
        "mem_lnx_nfs_unstable",
        "mem_lnx_writeback_tmp",
    ],
    # see mem_linux.py: Pending is the sum of the stacked metrics
    simple_lines=["mem_lnx_pending"],
    optional=["mem_lnx_pending"],
)
