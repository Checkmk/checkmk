#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.graphing.v1 import graphs, metrics, Title

UNIT = metrics.Unit(metrics.DecimalNotation(""))

metric_volume_total_number = metrics.Metric(
    name="podman_disk_usage_volumes_total_number",
    title=Title("Number of Podman volumes"),
    unit=UNIT,
    color=metrics.Color.CYAN,
)

metric_volume_active_number = metrics.Metric(
    name="podman_disk_usage_volumes_active_number",
    title=Title("Number of active Podman volumes"),
    unit=UNIT,
    color=metrics.Color.GREEN,
)

graph_podman_disk_usage_volumes_objects = graphs.Graph(
    name="podman_disk_usage_volumes_objects",
    title=Title("Number of volumes"),
    simple_lines=["podman_disk_usage_volumes_total_number"],
    compound_lines=["podman_disk_usage_volumes_active_number"],
)
