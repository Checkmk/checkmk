#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

metric_kube_agent_watch_errors = metrics.Metric(
    name="kube_agent_watch_errors",
    title=Title("Watch errors since cluster-aggregator start"),
    unit=metrics.Unit(metrics.DecimalNotation("")),
    color=metrics.Color.RED,
)

metric_kube_agent_relist_age = metrics.Metric(
    name="kube_agent_relist_age",
    title=Title("Ongoing list duration"),
    unit=metrics.Unit(metrics.TimeNotation()),
    color=metrics.Color.ORANGE,
)

metric_kube_agent_relist_duration = metrics.Metric(
    name="kube_agent_relist_duration",
    title=Title("Last completed list duration"),
    unit=metrics.Unit(metrics.TimeNotation()),
    color=metrics.Color.BLUE,
)
