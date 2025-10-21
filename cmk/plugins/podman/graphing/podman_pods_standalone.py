#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.graphing.v1 import metrics, Title

UNIT = metrics.Unit(metrics.DecimalNotation(""))

metric_created_number = metrics.Metric(
    name="podman_pods_created_number",
    title=Title("Number of created Podman pods"),
    unit=UNIT,
    color=metrics.Color.GREEN,
)

metric_stopped_number = metrics.Metric(
    name="podman_pods_stopped_number",
    title=Title("Number of stopped Podman pods"),
    unit=UNIT,
    color=metrics.Color.DARK_PURPLE,
)

metric_exited_number = metrics.Metric(
    name="podman_pods_exited_number",
    title=Title("Number of exited Podman pods"),
    unit=UNIT,
    color=metrics.Color.CYAN,
)
