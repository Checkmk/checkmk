#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_veeam_license_instances_percent = metrics.Metric(
    name="veeam_license_instances_percent",
    title=Title("Instance license consumption"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)

metric_veeam_license_sockets_percent = metrics.Metric(
    name="veeam_license_sockets_percent",
    title=Title("Socket license consumption"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)

metric_veeam_license_capacity_percent = metrics.Metric(
    name="veeam_license_capacity_percent",
    title=Title("Capacity license consumption"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)


graph_veeam_license_consumption = graphs.Graph(
    name="veeam_license_consumption",
    title=Title("License consumption"),
    simple_lines=[
        "veeam_license_instances_percent",
        "veeam_license_sockets_percent",
        "veeam_license_capacity_percent",
    ],
)
