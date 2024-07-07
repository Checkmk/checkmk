#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_zfs_metadata_limit = metrics.Metric(
    name="zfs_metadata_limit",
    title=Title("Limit of meta data"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_zfs_metadata_max = metrics.Metric(
    name="zfs_metadata_max",
    title=Title("Maxmimum of meta data"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_zfs_metadata_used = metrics.Metric(
    name="zfs_metadata_used",
    title=Title("Used meta data"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)

graph_zfs_meta_data = graphs.Graph(
    name="zfs_meta_data",
    title=Title("ZFS meta data"),
    simple_lines=[
        "zfs_metadata_max",
        "zfs_metadata_used",
        "zfs_metadata_limit",
    ],
)
