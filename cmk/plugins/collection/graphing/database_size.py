#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_allocated_size = metrics.Metric(
    name="allocated_size",
    title=Title("Allocated space"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_data_size = metrics.Metric(
    name="data_size",
    title=Title("Data size"),
    unit=UNIT_BYTES,
    color=metrics.Color.ORANGE,
)
metric_database_reclaimable = metrics.Metric(
    name="database_reclaimable",
    title=Title("Database reclaimable size"),
    unit=UNIT_BYTES,
    color=metrics.Color.GRAY,
)
metric_database_size = metrics.Metric(
    name="database_size",
    title=Title("Database size"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_indexes_size = metrics.Metric(
    name="indexes_size",
    title=Title("Index space"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_reserved_size = metrics.Metric(
    name="reserved_size",
    title=Title("Reserved space"),
    unit=UNIT_BYTES,
    color=metrics.Color.RED,
)
metric_unallocated_size = metrics.Metric(
    name="unallocated_size",
    title=Title("Unallocated space"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_unused_size = metrics.Metric(
    name="unused_size",
    title=Title("Unused space"),
    unit=UNIT_BYTES,
    color=metrics.Color.BROWN,
)

perfometer_database_size = perfometers.Perfometer(
    name="database_size",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(2000000000),
    ),
    segments=["database_size"],
)

graph_database_sizes = graphs.Graph(
    name="database_sizes",
    title=Title("Database sizes"),
    compound_lines=[
        "database_size",
        "unallocated_size",
        "reserved_size",
        "data_size",
        "indexes_size",
        "unused_size",
        "database_reclaimable",
    ],
    optional=[
        "unallocated_size",
        "reserved_size",
        "data_size",
        "indexes_size",
        "unused_size",
        "database_reclaimable",
    ],
)
graph_datafile_sizes = graphs.Graph(
    name="datafile_sizes",
    title=Title("Datafile sizes"),
    compound_lines=["data_size"],
    simple_lines=["allocated_size"],
)
