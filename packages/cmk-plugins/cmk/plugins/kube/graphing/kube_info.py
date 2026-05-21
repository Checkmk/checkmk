#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, perfometers, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_kube_info_age = metrics.Metric(
    name="kube_info_age",
    title=Title("Age"),
    unit=UNIT_TIME,
    color=metrics.Color.CYAN,
)

perfometer_kube_info_age = perfometers.Perfometer(
    name="kube_info_age",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        # 30 days. The host Uptime perfometer uses ~58 days, but Kubernetes
        # workloads turn over much more often than long-lived hosts (rolling
        # updates, redeployments, ephemeral jobs), so a shorter linear range
        # keeps typical pod ages visually informative. The arctan tail still
        # handles older long-lived workloads without the bar reaching full.
        perfometers.Open(2592000),
    ),
    segments=["kube_info_age"],
)
