#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_connections_perc_conn_threads = metrics.Metric(
    name="connections_perc_conn_threads",
    title=Title("Open connections load"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_connections_perc_used = metrics.Metric(
    name="connections_perc_used",
    title=Title("Parallel connections load"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)

perfometer_connections_perc_conn_threads_connections_perc_used = perfometers.Stacked(
    name="connections_perc_conn_threads_connections_perc_used",
    lower=perfometers.Perfometer(
        name="connections_perc_conn_threads",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(100),
        ),
        segments=["connections_perc_conn_threads"],
    ),
    upper=perfometers.Perfometer(
        name="connections_perc_used",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Closed(100),
        ),
        segments=["connections_perc_used"],
    ),
)
