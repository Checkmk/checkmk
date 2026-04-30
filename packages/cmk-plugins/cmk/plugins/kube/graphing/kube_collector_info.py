#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_kube_cluster_collector_container_metrics_cache_size = metrics.Metric(
    name="kube_cluster_collector_container_metrics_cache_size",
    title=Title("Cluster collector: Container metrics cache size"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)

metric_kube_cluster_collector_machine_sections_cache_size = metrics.Metric(
    name="kube_cluster_collector_machine_sections_cache_size",
    title=Title("Cluster collector: Machine sections cache size"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
