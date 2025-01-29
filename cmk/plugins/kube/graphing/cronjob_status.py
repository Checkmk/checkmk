#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_kube_cron_job_status_job_duration = metrics.Metric(
    name="kube_cron_job_status_job_duration",
    title=Title("Total duration"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_kube_cron_job_status_execution_duration = metrics.Metric(
    name="kube_cron_job_status_execution_duration",
    title=Title("Execution time"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)

graph_kube_cronjob_status = graphs.Graph(
    name="kube_cronjob_status",
    title=Title("Duration"),
    simple_lines=[
        "kube_cron_job_status_job_duration",
        "kube_cron_job_status_execution_duration",
    ],
)
