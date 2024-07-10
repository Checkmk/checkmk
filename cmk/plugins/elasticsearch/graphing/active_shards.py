#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_active_primary_shards = metrics.Metric(
    name="active_primary_shards",
    title=Title("Active primary shards"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_active_shards = metrics.Metric(
    name="active_shards",
    title=Title("Active shards"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_initializing_shards = metrics.Metric(
    name="initializing_shards",
    title=Title("Initializing shards"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PINK,
)
metric_relocating_shards = metrics.Metric(
    name="relocating_shards",
    title=Title("Relocating shards"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_unassigned_shards = metrics.Metric(
    name="unassigned_shards",
    title=Title("Unassigned shards"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)

perfometer_active_shards = perfometers.Bidirectional(
    name="active_shards",
    left=perfometers.Perfometer(
        name="active_primary_shards",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed("active_shards"),
        ),
        segments=["active_primary_shards"],
    ),
    right=perfometers.Perfometer(
        name="active_shards",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed("active_shards"),
        ),
        segments=["active_shards"],
    ),
)

graph_shards_allocation = graphs.Graph(
    name="shards_allocation",
    title=Title("Shard allocation over time"),
    simple_lines=[
        "active_shards",
        "active_primary_shards",
        "relocating_shards",
        "initializing_shards",
        "unassigned_shards",
    ],
)
graph_active_shards = graphs.Graph(
    name="active_shards",
    title=Title("Active shards"),
    simple_lines=[
        "active_shards",
        "active_primary_shards",
    ],
)
