#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_varnish_worker_create_rate = metrics.Metric(
    name="varnish_worker_create_rate",
    title=Title("Worker threads created"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_varnish_worker_drop_rate = metrics.Metric(
    name="varnish_worker_drop_rate",
    title=Title("Dropped work requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_varnish_worker_failed_rate = metrics.Metric(
    name="varnish_worker_failed_rate",
    title=Title("Worker threads not created"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_varnish_worker_lqueue_rate = metrics.Metric(
    name="varnish_worker_lqueue_rate",
    title=Title("Work request queue length"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.RED,
)
metric_varnish_worker_max_rate = metrics.Metric(
    name="varnish_worker_max_rate",
    title=Title("Worker threads limited"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_varnish_worker_queued_rate = metrics.Metric(
    name="varnish_worker_queued_rate",
    title=Title("Queued work requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_varnish_worker_rate = metrics.Metric(
    name="varnish_worker_rate",
    title=Title("Worker threads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)

graph_varnish_worker = graphs.Graph(
    name="varnish_worker",
    title=Title("Varnish Worker"),
    simple_lines=[
        "varnish_worker_lqueue_rate",
        "varnish_worker_create_rate",
        "varnish_worker_drop_rate",
        "varnish_worker_rate",
        "varnish_worker_failed_rate",
        "varnish_worker_queued_rate",
        "varnish_worker_max_rate",
    ],
)
