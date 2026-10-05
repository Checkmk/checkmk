#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""))

metric_5ghz_clients = metrics.Metric(
    name="5ghz_clients",
    title=Title("Client connects for 5 Ghz band"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_PINK,
)
metric_24ghz_clients = metrics.Metric(
    name="24ghz_clients",
    title=Title("Client connects for 2,4 Ghz band"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_active_vpn_users = metrics.Metric(
    name="active_vpn_users",
    title=Title("Active VPN users"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_active_vpn_websessions = metrics.Metric(
    name="active_vpn_websessions",
    title=Title("Active VPN web sessions"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_fortiauthenticator_fails_5min = metrics.Metric(
    name="fortiauthenticator_fails_5min",
    title=Title("Authentication failures (last 5 minutes)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_fortigate_detection_rate = metrics.Metric(
    name="fortigate_detection_rate",
    title=Title("Detection rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_fortigate_blocking_rate = metrics.Metric(
    name="fortigate_blocking_rate",
    title=Title("Blocking rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_load_instant = metrics.Metric(
    name="load_instant",
    title=Title("Instantaneous CPU load"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)
