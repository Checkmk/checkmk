#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_veeam_license_expiry = metrics.Metric(
    name="veeam_license_expiry",
    title=Title("Time until license expiry"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)

metric_veeam_license_support_expiry = metrics.Metric(
    name="veeam_license_support_expiry",
    title=Title("Time until support expiry"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)


graph_veeam_license_expiry = graphs.Graph(
    name="veeam_license_expiry",
    title=Title("License and support expiry"),
    simple_lines=[
        "veeam_license_expiry",
        "veeam_license_support_expiry",
    ],
)
