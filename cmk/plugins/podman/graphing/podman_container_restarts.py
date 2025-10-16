#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.graphing.v1 import metrics, Title

UNIT = metrics.Unit(metrics.DecimalNotation(""))

metric_container_restarts_total = metrics.Metric(
    name="podman_container_restarts_total",
    title=Title("Total restarts"),
    unit=UNIT,
    color=metrics.Color.BLUE,
)
metric_container_restarts_last_hour = metrics.Metric(
    name="podman_container_restarts_last_hour",
    title=Title("Restarts within the last hour"),
    unit=UNIT,
    color=metrics.Color.GREEN,
)
