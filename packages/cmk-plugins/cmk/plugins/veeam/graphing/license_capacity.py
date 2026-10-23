#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.SINotation("B"))

metric_veeam_license_capacity_used = metrics.Metric(
    name="veeam_license_capacity_used",
    title=Title("Capacity used"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)

metric_veeam_license_capacity_licensed = metrics.Metric(
    name="veeam_license_capacity_licensed",
    title=Title("Capacity licensed"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLACK,
)


graph_veeam_license_capacity = graphs.Graph(
    name="veeam_license_capacity",
    title=Title("Capacity licenses"),
    compound_lines=["veeam_license_capacity_used"],
    simple_lines=["veeam_license_capacity_licensed"],
)
