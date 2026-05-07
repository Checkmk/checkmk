#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_connections_total = metrics.Metric(
    name="connections_total",
    title=Title("Accepted connection requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_clients_rejected = metrics.Metric(
    name="clients_rejected",
    title=Title("Rejected connection requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
metric_clients_output = metrics.Metric(
    name="clients_output",
    title=Title("Longest output list"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_clients_input = metrics.Metric(
    name="clients_input",
    title=Title("Biggest input buffer"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_clients_blocked = metrics.Metric(
    name="clients_blocked",
    title=Title("Clients pending on a blocking call"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_changes_sld = metrics.Metric(
    name="changes_sld",
    title=Title("Changes since last dump"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
