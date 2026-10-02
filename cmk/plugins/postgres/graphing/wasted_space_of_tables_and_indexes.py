#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_indexspace_wasted = metrics.Metric(
    name="indexspace_wasted",
    title=Title("Indexspace wasted"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_tablespace_wasted = metrics.Metric(
    name="tablespace_wasted",
    title=Title("Tablespace wasted"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)

perfometer_indexspace_wasted_tablespace_wasted = perfometers.Stacked(
    name="indexspace_wasted_tablespace_wasted",
    lower=perfometers.Perfometer(
        name="indexspace_wasted",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(2000000),
        ),
        segments=["indexspace_wasted"],
    ),
    upper=perfometers.Perfometer(
        name="tablespace_wasted",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(2000000),
        ),
        segments=["tablespace_wasted"],
    ),
)

graph_wasted_space_of_tables_and_indexes = graphs.Graph(
    name="wasted_space_of_tables_and_indexes",
    title=Title("Wasted space of tables and indexes"),
    compound_lines=[
        "tablespace_wasted",
        "indexspace_wasted",
    ],
)
