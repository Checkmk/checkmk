#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.graphing.v1 import graphs, metrics, Title

UNIT = metrics.Unit(metrics.DecimalNotation(""))

metric_image_total_number = metrics.Metric(
    name="podman_disk_usage_images_total_number",
    title=Title("Number of Podman images"),
    unit=UNIT,
    color=metrics.Color.CYAN,
)

metric_image_active_number = metrics.Metric(
    name="podman_disk_usage_images_active_number",
    title=Title("Number of active Podman images"),
    unit=UNIT,
    color=metrics.Color.GREEN,
)

graph_podman_disk_usage_images_objects = graphs.Graph(
    name="podman_disk_usage_images_objects",
    title=Title("Number of images"),
    simple_lines=["podman_disk_usage_images_total_number"],
    compound_lines=["podman_disk_usage_images_active_number"],
)
