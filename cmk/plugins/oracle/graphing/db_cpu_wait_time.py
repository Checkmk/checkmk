#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_oracle_db_cpu = metrics.Metric(
    name="oracle_db_cpu",
    title=Title("Oracle DB CPU time"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_oracle_db_wait_time = metrics.Metric(
    name="oracle_db_wait_time",
    title=Title("Oracle DB non-idle wait"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_oracle_db_time = metrics.Metric(
    name="oracle_db_time",
    title=Title("Oracle DB time"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)

perfometer_oracle_db_cpu_wait_time = perfometers.Perfometer(
    name="oracle_db_cpu_wait_time",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(
            metrics.Constant(
                Title(""),
                UNIT_COUNTER,
                metrics.Color.BLUE,
                50.0,
            )
        ),
    ),
    segments=[
        "oracle_db_cpu",
        "oracle_db_wait_time",
    ],
)

graph_oracle_db_time_statistics = graphs.Graph(
    name="oracle_db_time_statistics",
    title=Title("Oracle DB time statistics"),
    compound_lines=[
        "oracle_db_cpu",
        "oracle_db_wait_time",
    ],
    simple_lines=["oracle_db_time"],
    optional=["oracle_db_wait_time"],
)
