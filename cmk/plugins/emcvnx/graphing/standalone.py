#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_emcvnx_over_subscribed = metrics.Metric(
    name="emcvnx_over_subscribed",
    title=Title("Oversubscribed"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_PINK,
)
metric_emcvnx_total_subscribed_capacity = metrics.Metric(
    name="emcvnx_total_subscribed_capacity",
    title=Title("Total subscribed capacity"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)
metric_emcvnx_perc_full = metrics.Metric(
    name="emcvnx_perc_full",
    title=Title("Percent full"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_emcvnx_perc_subscribed = metrics.Metric(
    name="emcvnx_perc_subscribed",
    title=Title("Percent subscribed"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_emcvnx_time_to_complete = metrics.Metric(
    name="emcvnx_time_to_complete",
    title=Title("Estimated time to complete"),
    unit=UNIT_TIME,
    color=metrics.Color.CYAN,
)
metric_emcvnx_dedupl_perc_completed = metrics.Metric(
    name="emcvnx_dedupl_perc_completed",
    title=Title("Deduplication percent completed"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_emcvnx_dedupl_efficiency_savings = metrics.Metric(
    name="emcvnx_dedupl_efficiency_savings",
    title=Title("Deduplication efficiency savings"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_emcvnx_dedupl_shared_capacity = metrics.Metric(
    name="emcvnx_dedupl_shared_capacity",
    title=Title("Deduplication shared capacity"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)
