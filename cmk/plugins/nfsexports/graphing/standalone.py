#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))
UNIT_BYTES_PER_OPERATION = metrics.Unit(metrics.IECNotation("B/op"))
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_rpc_backlog = metrics.Metric(
    name="rpc_backlog",
    title=Title("RPC Backlog"),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_GREEN,
)
metric_read_ops = metrics.Metric(
    name="read_ops",
    title=Title("Read operations"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_read_b_s = metrics.Metric(
    name="read_b_s",
    title=Title("Read size per second"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
metric_read_b_op = metrics.Metric(
    name="read_b_op",
    title=Title("Read size per operation"),
    unit=UNIT_BYTES_PER_OPERATION,
    color=metrics.Color.DARK_CYAN,
)
metric_read_retrans = metrics.Metric(
    name="read_retrans",
    title=Title("Read retransmission"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_GREEN,
)
metric_write_retrans = metrics.Metric(
    name="write_retrans",
    title=Title("Write retransmission"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_GREEN,
)
metric_read_avg_rtt_s = metrics.Metric(
    name="read_avg_rtt_s",
    title=Title("Read average rtt"),
    unit=UNIT_TIME,
    color=metrics.Color.LIGHT_GREEN,
)
metric_read_avg_exe_s = metrics.Metric(
    name="read_avg_exe_s",
    title=Title("Read average exe"),
    unit=UNIT_TIME,
    color=metrics.Color.LIGHT_GREEN,
)
metric_write_ops_s = metrics.Metric(
    name="write_ops_s",
    title=Title("Write operations"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_write_b_s = metrics.Metric(
    name="write_b_s",
    title=Title("Writes size per second"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
metric_write_b_op = metrics.Metric(
    name="write_b_op",
    title=Title("Writes size per operation"),
    unit=UNIT_BYTES_PER_OPERATION,
    color=metrics.Color.DARK_CYAN,
)
metric_write_avg_rtt_s = metrics.Metric(
    name="write_avg_rtt_s",
    title=Title("Write average rtt"),
    unit=UNIT_TIME,
    color=metrics.Color.LIGHT_GREEN,
)
metric_write_avg_exe_s = metrics.Metric(
    name="write_avg_exe_s",
    title=Title("Write average exe"),
    unit=UNIT_TIME,
    color=metrics.Color.LIGHT_GREEN,
)
