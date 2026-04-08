#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import Color, DecimalNotation, Metric, StrictPrecision, Unit

COUNT_UNIT = Unit(DecimalNotation(""), StrictPrecision(0))

name_prefix_bazel_cache_metrics = "bazel_cache_metrics_"

metric_bazel_remote_incoming_requests_total_kind_ac_method_get_status_hit = Metric(
    name=f"{name_prefix_bazel_cache_metrics}bazel_remote_incoming_requests_total_kind_ac_method_get_status_hit",
    title=Title("Total number of incoming AC get cache request hits"),
    unit=COUNT_UNIT,
    color=Color.GREEN,
)
metric_bazel_remote_incoming_requests_total_kind_ac_method_get_status_miss = Metric(
    name=f"{name_prefix_bazel_cache_metrics}bazel_remote_incoming_requests_total_kind_ac_method_get_status_miss",
    title=Title("Total number of incoming AC get cache request misses"),
    unit=COUNT_UNIT,
    color=Color.PURPLE,
)

graph_bazel_remote_incoming_requests_totalkind_ac_method_get_status_hit = Graph(
    name=f"{name_prefix_bazel_cache_metrics}incoming_requests",
    title=Title("Incoming cache request hit"),
    simple_lines=(
        f"{name_prefix_bazel_cache_metrics}bazel_remote_incoming_requests_total_kind_ac_method_get_status_hit",
        f"{name_prefix_bazel_cache_metrics}bazel_remote_incoming_requests_total_kind_ac_method_get_status_miss",
    ),
)
