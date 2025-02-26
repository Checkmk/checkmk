#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_fs_free = metrics.Metric(
    name="fs_free",
    title=Title("Free space"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_fs_size = metrics.Metric(
    name="fs_size",
    title=Title("Total size"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_fs_used = metrics.Metric(
    name="fs_used",
    title=Title("Used space"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_logical_used = metrics.Metric(
    name="logical_used",
    title=Title("Used logical space"),
    unit=UNIT_BYTES,
    color=metrics.Color.BROWN,
)
metric_replication_size = metrics.Metric(
    name="replication_size",
    title=Title("Replication"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_reserved = metrics.Metric(
    name="reserved",
    title=Title("Reserved space"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_shared_size = metrics.Metric(
    name="shared_size",
    title=Title("Shared"),
    unit=UNIT_BYTES,
    color=metrics.Color.BROWN,
)
metric_snapshots_size = metrics.Metric(
    name="snapshots_size",
    title=Title("Snapshots"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_space_savings = metrics.Metric(
    name="space_savings",
    title=Title("Saved space"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_system_size = metrics.Metric(
    name="system_size",
    title=Title("System"),
    unit=UNIT_BYTES,
    color=metrics.Color.GRAY,
)
metric_unique_size = metrics.Metric(
    name="unique_size",
    title=Title("Unique"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_virtual_size = metrics.Metric(
    name="virtual_size",
    title=Title("Virtual"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)

graph_capacity_usage = graphs.Graph(
    name="capacity_usage",
    title=Title("Capacity usage"),
    compound_lines=[
        "unique_size",
        "snapshots_size",
        "shared_size",
        "system_size",
        "replication_size",
    ],
)
graph_capacity_usage_2 = graphs.Graph(
    name="capacity_usage_2",
    title=Title("Capacity usage"),
    simple_lines=[
        "fs_size",
        "unique_size",
        "snapshots_size",
        "virtual_size",
    ],
)
graph_fs_used = graphs.Graph(
    name="fs_used",
    title=Title("Size and used space"),
    minimal_range=graphs.MinimalRange(
        0,
        metrics.MaximumOf(
            "fs_used",
            metrics.Color.GRAY,
        ),
    ),
    compound_lines=[
        "fs_used",
        "fs_free",
    ],
    simple_lines=[
        "fs_size",
        metrics.WarningOf("fs_used"),
        metrics.CriticalOf("fs_used"),
    ],
    conflicting=["reserved"],
)
graph_fs_used_2 = graphs.Graph(
    name="fs_used_2",
    title=Title("Size and used space"),
    minimal_range=graphs.MinimalRange(
        0,
        metrics.MaximumOf(
            "fs_used",
            metrics.Color.GRAY,
        ),
    ),
    compound_lines=[
        "fs_used",
        "fs_free",
        "reserved",
    ],
    simple_lines=[
        metrics.Sum(
            Title("Filesystem size"),
            metrics.Color.DARK_GREEN,
            [
                "fs_used",
                "fs_free",
                "reserved",
            ],
        ),
        metrics.WarningOf("fs_used"),
        metrics.CriticalOf("fs_used"),
    ],
)
graph_savings = graphs.Graph(
    name="savings",
    title=Title("Space savings"),
    minimal_range=graphs.MinimalRange(
        0,
        metrics.MaximumOf(
            "logical_used",
            metrics.Color.GRAY,
        ),
    ),
    compound_lines=[
        "fs_used",
        "fs_free",
    ],
    simple_lines=[
        metrics.Sum(
            Title("Filesystem size"),
            metrics.Color.DARK_GREEN,
            [
                "fs_used",
                "fs_free",
            ],
        ),
        "logical_used",
        "space_savings",
        metrics.WarningOf("fs_used"),
        metrics.CriticalOf("fs_used"),
    ],
)
