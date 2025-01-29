#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_varnish_objects_expired_rate = metrics.Metric(
    name="varnish_objects_expired_rate",
    title=Title("Expired objects"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_varnish_objects_lru_moved_rate = metrics.Metric(
    name="varnish_objects_lru_moved_rate",
    title=Title("LRU moved objects"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_varnish_objects_lru_nuked_rate = metrics.Metric(
    name="varnish_objects_lru_nuked_rate",
    title=Title("LRU nuked objects"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)

graph_varnish_objects = graphs.Graph(
    name="varnish_objects",
    title=Title("Varnish Objects"),
    simple_lines=[
        "varnish_objects_expired_rate",
        "varnish_objects_lru_nuked_rate",
        "varnish_objects_lru_moved_rate",
    ],
)
