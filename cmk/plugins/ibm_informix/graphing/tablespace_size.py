#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_tablespace_max_size = metrics.Metric(
    name="tablespace_max_size",
    title=Title("Tablespace maximum size"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_tablespace_size = metrics.Metric(
    name="tablespace_size",
    title=Title("Tablespace size"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_tablespace_used = metrics.Metric(
    name="tablespace_used",
    title=Title("Tablespace used"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)

perfometer_tablespace_used = perfometers.Perfometer(
    name="tablespace_used",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed("tablespace_max_size"),
    ),
    segments=["tablespace_used"],
)

graph_tablespace_sizes = graphs.Graph(
    name="tablespace_sizes",
    title=Title("Tablespace sizes"),
    minimal_range=graphs.MinimalRange(
        0,
        "tablespace_max_size",
    ),
    compound_lines=["tablespace_used"],
    simple_lines=[
        "tablespace_size",
        metrics.WarningOf("tablespace_size"),
        metrics.CriticalOf("tablespace_size"),
    ],
)
