#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
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
metric_kube_available_replicas = metrics.Metric(
    name="kube_available_replicas",
    title=Title("Available replicas"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_kube_cpu_allocatable = metrics.Metric(
    name="kube_cpu_allocatable",
    title=Title("Allocatable"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)
metric_kube_cpu_limit = metrics.Metric(
    name="kube_cpu_limit",
    title=Title("Limits"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)
metric_kube_cpu_request = metrics.Metric(
    name="kube_cpu_request",
    title=Title("Requests"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)
metric_kube_cpu_usage = metrics.Metric(
    name="kube_cpu_usage",
    title=Title("Usage"),
    unit=UNIT_NUMBER,
    color=metrics.Color.CYAN,
)
metric_kube_cron_job_status_active = metrics.Metric(
    name="kube_cron_job_status_active",
    title=Title("Active jobs"),
    unit=UNIT_NUMBER,
    color=metrics.Color.CYAN,
)
metric_kube_cron_job_status_execution_duration = metrics.Metric(
    name="kube_cron_job_status_execution_duration",
    title=Title("Execution time"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)
metric_kube_cron_job_status_job_duration = metrics.Metric(
    name="kube_cron_job_status_job_duration",
    title=Title("Total duration"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
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
metric_kube_desired_replicas = metrics.Metric(
    name="kube_desired_replicas",
    title=Title("Desired replicas"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_kube_memory_allocatable = metrics.Metric(
    name="kube_memory_allocatable",
    title=Title("Allocatable"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
metric_kube_memory_limit = metrics.Metric(
    name="kube_memory_limit",
    title=Title("Limits"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_kube_memory_request = metrics.Metric(
    name="kube_memory_request",
    title=Title("Requests"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_kube_memory_usage = metrics.Metric(
    name="kube_memory_usage",
    title=Title("Usage"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)
metric_kube_misscheduled_replicas = metrics.Metric(
    name="kube_misscheduled_replicas",
    title=Title("Misscheduled replicas"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_kube_node_container_count_running = metrics.Metric(
    name="kube_node_container_count_running",
    title=Title("Running containers"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_kube_node_container_count_terminated = metrics.Metric(
    name="kube_node_container_count_terminated",
    title=Title("Terminated containers"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_kube_node_container_count_total = metrics.Metric(
    name="kube_node_container_count_total",
    title=Title("Total containers"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_kube_node_container_count_waiting = metrics.Metric(
    name="kube_node_container_count_waiting",
    title=Title("Waiting containers"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_kube_node_count_control_plane_not_ready = metrics.Metric(
    name="kube_node_count_control_plane_not_ready",
    title=Title("Control plane nodes not ready"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_kube_node_count_control_plane_ready = metrics.Metric(
    name="kube_node_count_control_plane_ready",
    title=Title("Control plane nodes ready"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_kube_node_count_control_plane_total = metrics.Metric(
    name="kube_node_count_control_plane_total",
    title=Title("Control plane nodes total"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_kube_node_count_worker_not_ready = metrics.Metric(
    name="kube_node_count_worker_not_ready",
    title=Title("Worker nodes not ready"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_kube_node_count_worker_ready = metrics.Metric(
    name="kube_node_count_worker_ready",
    title=Title("Worker nodes ready"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_kube_node_count_worker_total = metrics.Metric(
    name="kube_node_count_worker_total",
    title=Title("Worker nodes total"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_kube_pod_allocatable = metrics.Metric(
    name="kube_pod_allocatable",
    title=Title("Allocatable"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_kube_pod_failed = metrics.Metric(
    name="kube_pod_failed",
    title=Title("Failed"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_kube_pod_free = metrics.Metric(
    name="kube_pod_free",
    title=Title("Free"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_kube_pod_pending = metrics.Metric(
    name="kube_pod_pending",
    title=Title("Pending"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_kube_pod_restart_count = metrics.Metric(
    name="kube_pod_restart_count",
    title=Title("Restarts"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)
metric_kube_pod_restart_rate = metrics.Metric(
    name="kube_pod_restart_rate",
    title=Title("Restarts per hour"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)
metric_kube_pod_running = metrics.Metric(
    name="kube_pod_running",
    title=Title("Running"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_kube_pod_succeeded = metrics.Metric(
    name="kube_pod_succeeded",
    title=Title("Succeeded"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_kube_ready_replicas = metrics.Metric(
    name="kube_ready_replicas",
    title=Title("Ready replicas"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_kube_updated_replicas = metrics.Metric(
    name="kube_updated_replicas",
    title=Title("Up-to-date replicas"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)

perfometer_kube_cpu_usage = perfometers.Perfometer(
    name="kube_cpu_usage",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(1),
    ),
    segments=["kube_cpu_usage"],
)
perfometer_kube_memory_usage = perfometers.Perfometer(
    name="kube_memory_usage",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(1000000000),
    ),
    segments=["kube_memory_usage"],
)

graph_kube_cpu_usage = graphs.Graph(
    name="kube_cpu_usage",
    title=Title("CPU"),
    compound_lines=["kube_cpu_usage"],
    simple_lines=[
        "kube_cpu_request",
        "kube_cpu_limit",
        "kube_cpu_allocatable",
        metrics.WarningOf("kube_cpu_usage"),
        metrics.CriticalOf("kube_cpu_usage"),
    ],
    optional=[
        "kube_cpu_request",
        "kube_cpu_limit",
        "kube_cpu_usage",
        "kube_cpu_allocatable",
    ],
)
graph_kube_cronjob_status = graphs.Graph(
    name="kube_cronjob_status",
    title=Title("Duration"),
    simple_lines=[
        "kube_cron_job_status_job_duration",
        "kube_cron_job_status_execution_duration",
    ],
)
graph_kube_memory_usage = graphs.Graph(
    name="kube_memory_usage",
    title=Title("Memory"),
    compound_lines=["kube_memory_usage"],
    simple_lines=[
        "kube_memory_request",
        "kube_memory_limit",
        "kube_memory_allocatable",
        metrics.WarningOf("kube_memory_usage"),
        metrics.CriticalOf("kube_memory_usage"),
    ],
    optional=[
        "kube_memory_request",
        "kube_memory_limit",
        "kube_memory_usage",
        "kube_memory_allocatable",
    ],
)
graph_kube_node_container_count = graphs.Graph(
    name="kube_node_container_count",
    title=Title("Containers"),
    compound_lines=[
        "kube_node_container_count_running",
        "kube_node_container_count_waiting",
        "kube_node_container_count_terminated",
    ],
    simple_lines=[
        "kube_node_container_count_total",
        metrics.WarningOf("kube_node_container_count_total"),
        metrics.CriticalOf("kube_node_container_count_total"),
    ],
)
graph_kube_node_count_control_plane = graphs.Graph(
    name="kube_node_count_control_plane",
    title=Title("Control plane nodes"),
    compound_lines=[
        "kube_node_count_control_plane_ready",
        "kube_node_count_control_plane_not_ready",
    ],
    simple_lines=["kube_node_count_control_plane_total"],
)
graph_kube_node_count_worker = graphs.Graph(
    name="kube_node_count_worker",
    title=Title("Worker nodes"),
    compound_lines=[
        "kube_node_count_worker_ready",
        "kube_node_count_worker_not_ready",
    ],
    simple_lines=["kube_node_count_worker_total"],
)
graph_kube_pod_resources = graphs.Graph(
    name="kube_pod_resources",
    title=Title("Allocated pod resources"),
    compound_lines=[
        "kube_pod_running",
        "kube_pod_pending",
        "kube_pod_free",
    ],
    simple_lines=["kube_pod_allocatable"],
    optional=[
        "kube_pod_free",
        "kube_pod_allocatable",
    ],
)
graph_kube_pod_restarts = graphs.Graph(
    name="kube_pod_restarts",
    title=Title("Pod Restarts"),
    simple_lines=[
        "kube_pod_restart_count",
        "kube_pod_restart_rate",
    ],
    optional=["kube_pod_restart_rate"],
)
graph_kube_replica_available_state = graphs.Graph(
    name="kube_replica_available_state",
    title=Title("Replica available state"),
    compound_lines=["kube_available_replicas"],
    simple_lines=["kube_desired_replicas"],
    optional=["kube_available_replicas"],
)
graph_kube_replica_state = graphs.Graph(
    name="kube_replica_state",
    title=Title("Replica ready state"),
    compound_lines=["kube_ready_replicas"],
    simple_lines=["kube_desired_replicas"],
)
graph_kube_replica_update_state = graphs.Graph(
    name="kube_replica_update_state",
    title=Title("Replica update state"),
    compound_lines=["kube_updated_replicas"],
    simple_lines=["kube_desired_replicas"],
)
graph_kube_resources_terminated = graphs.Graph(
    name="kube_resources_terminated",
    title=Title("Terminated pod resources"),
    simple_lines=[
        "kube_pod_succeeded",
        "kube_pod_failed",
    ],
)
