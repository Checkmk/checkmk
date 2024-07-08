#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_mem_lnx_bounce = metrics.Metric(
    name="mem_lnx_bounce",
    title=Title("Bounce buffers"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
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

graph_filesystem_writeback = graphs.Graph(
    name="filesystem_writeback",
    title=Title("Filesystem writeback"),
    compound_lines=[
        "mem_lnx_dirty",
        "mem_lnx_writeback",
        "mem_lnx_nfs_unstable",
        "mem_lnx_bounce",
        "mem_lnx_writeback_tmp",
    ],
)
