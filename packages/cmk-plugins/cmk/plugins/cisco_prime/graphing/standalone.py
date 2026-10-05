#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_wifi_connection_dot11ax2_4 = metrics.Metric(
    name="wifi_connection_dot11ax2_4",
    title=Title("802.dot11ax2_4"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_wifi_connection_dot11ax5 = metrics.Metric(
    name="wifi_connection_dot11ax5",
    title=Title("802.dot11ax5"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_ap_count = metrics.Metric(
    name="ap_count",
    title=Title("Number of access points"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_clients_count = metrics.Metric(
    name="clients_count",
    title=Title("Number of clients"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
