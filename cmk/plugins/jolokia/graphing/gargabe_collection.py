#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_jvm_garbage_collection_count = metrics.Metric(
    name="jvm_garbage_collection_count",
    title=Title("Garbage collections"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_jvm_garbage_collection_time = metrics.Metric(
    name="jvm_garbage_collection_time",
    title=Title("Time spent collecting garbage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
