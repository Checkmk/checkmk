#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_ucwa_active_sessions_android = metrics.Metric(
    name="ucwa_active_sessions_android",
    title=Title("UCWA - Active sessions (Android)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_ucwa_active_sessions_ipad = metrics.Metric(
    name="ucwa_active_sessions_ipad",
    title=Title("UCWA - Active sessions (iPad)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_ucwa_active_sessions_iphone = metrics.Metric(
    name="ucwa_active_sessions_iphone",
    title=Title("UCWA - Active sessions (iPhone)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_ucwa_active_sessions_mac = metrics.Metric(
    name="ucwa_active_sessions_mac",
    title=Title("UCWA - Active sessions (Mac)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)

graph_active_sessions = graphs.Graph(
    name="active_sessions",
    title=Title("Active Sessions"),
    compound_lines=[
        "ucwa_active_sessions_mac",
        "ucwa_active_sessions_ipad",
        "ucwa_active_sessions_iphone",
        "ucwa_active_sessions_android",
    ],
)
