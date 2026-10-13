#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_items_active = metrics.Metric(
    name="items_active",
    title=Title("Active items"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_items_non_res = metrics.Metric(
    name="items_non_res",
    title=Title("Non-resident items"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_item_memory = metrics.Metric(
    name="item_memory",
    title=Title("Item memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_resident_items_ratio = metrics.Metric(
    name="resident_items_ratio",
    title=Title("Resident items ratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_fetched_items = metrics.Metric(
    name="fetched_items",
    title=Title("Number of fetched items"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_YELLOW,
)
metric_cache_misses_rate = metrics.Metric(
    name="cache_misses_rate",
    title=Title("Cache misses per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_size_on_disk = metrics.Metric(
    name="size_on_disk",
    title=Title("Size on disk"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_YELLOW,
)
metric_disk_fill_rate = metrics.Metric(
    name="disk_fill_rate",
    title=Title("Disk fill rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_disk_drain_rate = metrics.Metric(
    name="disk_drain_rate",
    title=Title("Disk drain rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)
