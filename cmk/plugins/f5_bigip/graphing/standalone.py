#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_connections_ssl = metrics.Metric(
    name="connections_ssl",
    title=Title("SSL connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_PINK,
)
metric_connections_ssl_vpn = metrics.Metric(
    name="connections_ssl_vpn",
    title=Title("SSL/VPN connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_PINK,
)
metric_packet_velocity_asic = metrics.Metric(
    name="packet_velocity_asic",
    title=Title("Packet velocity ASIC"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
