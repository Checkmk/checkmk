#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))

metric_cifs_read_data = metrics.Metric(
    name="cifs_read_data",
    title=Title("CIFS data read"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_cifs_write_data = metrics.Metric(
    name="cifs_write_data",
    title=Title("CIFS data written"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)

graph_cifs_traffic = graphs.Bidirectional(
    name="cifs_traffic",
    title=Title("CIFS traffic"),
    lower=graphs.Graph(
        name="cifs_traffic_lower",
        title=Title("CIFS traffic"),
        compound_lines=["cifs_read_data"],
    ),
    upper=graphs.Graph(
        name="cifs_traffic_upper",
        title=Title("CIFS traffic"),
        compound_lines=["cifs_write_data"],
    ),
)
