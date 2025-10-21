#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_image_total_size = metrics.Metric(
    name="podman_disk_usage_images_total_size",
    title=Title("Total size of Podman images"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)

perfometer_images_size = perfometers.Perfometer(
    name="podman_disk_usage_images_total_size",
    focus_range=perfometers.FocusRange(
        lower=perfometers.Closed(0),
        upper=perfometers.Open(
            metrics.MaximumOf(
                "podman_disk_usage_images_total_size",
                metrics.Color.GRAY,
            )
        ),
    ),
    segments=["podman_disk_usage_images_total_size"],
)

graph_podman_disk_usage_images = graphs.Graph(
    name="podman_disk_usage_images",
    title=Title("Disk Usage"),
    simple_lines=["podman_disk_usage_images_total_size"],
)
