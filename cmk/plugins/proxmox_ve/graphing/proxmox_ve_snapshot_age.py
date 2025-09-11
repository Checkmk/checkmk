#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_oldest_snapshot_age = metrics.Metric(
    name="oldest_snapshot_age",
    title=Title("Oldest snapshot age"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)

metric_newest_snapshot_age = metrics.Metric(
    name="newest_snapshot_age",
    title=Title("Newest snapshot age"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)

graph_snapshot_age = graphs.Graph(
    name="snapshot_age",
    title=Title("Snapshot Age"),
    simple_lines=["oldest_snapshot_age"],
    compound_lines=["newest_snapshot_age"],
)
