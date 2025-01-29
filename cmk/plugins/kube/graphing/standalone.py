#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_kube_memory_request_utilization = metrics.Metric(
    name="kube_memory_request_utilization",
    title=Title("Requests utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_kube_memory_limit_utilization = metrics.Metric(
    name="kube_memory_limit_utilization",
    title=Title("Limits utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_kube_memory_cluster_allocatable_utilization = metrics.Metric(
    name="kube_memory_cluster_allocatable_utilization",
    title=Title("Cluster utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_kube_memory_node_allocatable_utilization = metrics.Metric(
    name="kube_memory_node_allocatable_utilization",
    title=Title("Node utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_kube_cpu_request_utilization = metrics.Metric(
    name="kube_cpu_request_utilization",
    title=Title("Requests utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_kube_cpu_limit_utilization = metrics.Metric(
    name="kube_cpu_limit_utilization",
    title=Title("Limits utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_kube_cpu_cluster_allocatable_utilization = metrics.Metric(
    name="kube_cpu_cluster_allocatable_utilization",
    title=Title("Cluster utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_kube_cpu_node_allocatable_utilization = metrics.Metric(
    name="kube_cpu_node_allocatable_utilization",
    title=Title("Node utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_kube_cron_job_status_active = metrics.Metric(
    name="kube_cron_job_status_active",
    title=Title("Active jobs"),
    unit=UNIT_NUMBER,
    color=metrics.Color.CYAN,
)
metric_kube_cron_job_status_last_duration = metrics.Metric(
    name="kube_cron_job_status_last_duration",
    title=Title("Last completed duration"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_BLUE,
)
metric_kube_cron_job_status_since_completion = metrics.Metric(
    name="kube_cron_job_status_since_completion",
    title=Title("Time since last successful completion"),
    unit=UNIT_TIME,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_kube_cron_job_status_since_schedule = metrics.Metric(
    name="kube_cron_job_status_since_schedule",
    title=Title("Time since last successful schedule"),
    unit=UNIT_TIME,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_kube_misscheduled_replicas = metrics.Metric(
    name="kube_misscheduled_replicas",
    title=Title("Misscheduled replicas"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
