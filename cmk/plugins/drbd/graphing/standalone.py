#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_activity_log_updates = metrics.Metric(
    name="activity_log_updates",
    title=Title("Activity log updates"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_bit_map_updates = metrics.Metric(
    name="bit_map_updates",
    title=Title("Bit map updates"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_local_count_requests = metrics.Metric(
    name="local_count_requests",
    title=Title("Local count requests"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_YELLOW,
)
metric_pending_requests = metrics.Metric(
    name="pending_requests",
    title=Title("Pending requests"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_unacknowledged_requests = metrics.Metric(
    name="unacknowledged_requests",
    title=Title("Unacknowledged requests"),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_application_pending_requests = metrics.Metric(
    name="application_pending_requests",
    title=Title("Application pending requests"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_epoch_objects = metrics.Metric(
    name="epoch_objects",
    title=Title("Epoch objects"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_kb_out_of_sync = metrics.Metric(
    name="kb_out_of_sync",
    title=Title("Out of sync"),
    unit=UNIT_BYTES,
    color=metrics.Color.ORANGE,
)
