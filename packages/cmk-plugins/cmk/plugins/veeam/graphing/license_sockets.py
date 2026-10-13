#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNT = metrics.Unit(metrics.DecimalNotation(""))

metric_veeam_license_sockets_used = metrics.Metric(
    name="veeam_license_sockets_used",
    title=Title("Sockets used"),
    unit=UNIT_COUNT,
    color=metrics.Color.ORANGE,
)

metric_veeam_license_sockets_licensed = metrics.Metric(
    name="veeam_license_sockets_licensed",
    title=Title("Sockets licensed"),
    unit=UNIT_COUNT,
    color=metrics.Color.BLACK,
)


graph_veeam_license_sockets = graphs.Graph(
    name="veeam_license_sockets",
    title=Title("Socket licenses"),
    compound_lines=["veeam_license_sockets_used"],
    simple_lines=["veeam_license_sockets_licensed"],
)
