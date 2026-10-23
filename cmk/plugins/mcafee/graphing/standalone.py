#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_tcp_packets_received = metrics.Metric(
    name="tcp_packets_received",
    title=Title("Received TCP packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_udp_packets_received = metrics.Metric(
    name="udp_packets_received",
    title=Title("Received UDP packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_icmp_packets_received = metrics.Metric(
    name="icmp_packets_received",
    title=Title("Received ICMP packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_time_to_resolve_dns = metrics.Metric(
    name="time_to_resolve_dns",
    title=Title("Time to resolve DNS"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_time_consumed_by_rule_engine = metrics.Metric(
    name="time_consumed_by_rule_engine",
    title=Title("Time consumed by rule engine"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
