#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_last_sync_receive_time = metrics.Metric(
    name="last_sync_receive_time",
    title=Title("Time since last NTPMessage"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_last_sync_time = metrics.Metric(
    name="last_sync_time",
    title=Title("Time since last sync"),
    unit=UNIT_TIME,
    color=metrics.Color.LIGHT_BLUE,
)

graph_last_sync_time = graphs.Graph(
    name="last_sync_time",
    title=Title("Time since last synchronisation"),
    simple_lines=[
        "last_sync_time",
        "last_sync_receive_time",
    ],
)
