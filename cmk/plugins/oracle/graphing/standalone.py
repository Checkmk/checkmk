#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())
UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_oracle_number_of_nodes_not_in_target_state = metrics.Metric(
    name="oracle_number_of_nodes_not_in_target_state",
    title=Title("Oracle number of nodes in target state"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_YELLOW,
)
metric_apply_finish_time = metrics.Metric(
    name="apply_finish_time",
    title=Title("Apply finish time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_transport_lag = metrics.Metric(
    name="transport_lag",
    title=Title("Transport lag"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_managed_object_count = metrics.Metric(
    name="managed_object_count",
    title=Title("Managed objects"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_storage_used = metrics.Metric(
    name="storage_used",
    title=Title("Storage space used"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
