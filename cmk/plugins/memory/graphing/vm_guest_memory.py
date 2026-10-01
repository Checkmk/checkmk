#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"), metrics.StrictPrecision(2))

metric_balloon = metrics.Metric(
    name="balloon",
    title=Title("Balloon memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.PINK,
)
metric_unaccepted = metrics.Metric(
    name="unaccepted",
    title=Title("Unaccepted memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.GRAY,
)

graph_vm_guest_memory = graphs.Graph(
    name="vm_guest_memory",
    title=Title("VM guest memory"),
    simple_lines=[
        "balloon",
        "unaccepted",
    ],
    # Balloon exists since kernel 6.15, Unaccepted since 6.5 and only with
    # CONFIG_UNACCEPTED_MEMORY, so a host may report either one alone.
    optional=[
        "balloon",
        "unaccepted",
    ],
)
