#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_server_conns = metrics.Metric(
    name="server_conns",
    title=Title("Server connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_client_conns = metrics.Metric(
    name="client_conns",
    title=Title("Client connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
