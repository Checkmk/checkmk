#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.metrics.utils import graph_info, metric_info

###########################################################################
# NOTE: These metrics (and associated special agent/checks) are deprecated and
#       will be removed in Checkmk version 2.2.
###########################################################################


# .
#   .--Metrics-------------------------------------------------------------.
#   |                   __  __      _        _                             |
#   |                  |  \/  | ___| |_ _ __(_) ___ ___                    |
#   |                  | |\/| |/ _ \ __| '__| |/ __/ __|                   |
#   |                  | |  | |  __/ |_| |  | | (__\__ \                   |
#   |                  |_|  |_|\___|\__|_|  |_|\___|___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Definitions of metrics                                              |
#   '----------------------------------------------------------------------'

# Title are always lower case - except the first character!
# Colors: See indexed_color() in cmk/gui/plugins/metrics/utils.py

metric_info["k8s_nodes"] = {  # legacy kubernetes checks
    "title": _("Nodes"),
    "unit": "count",
    "color": "11/a",
}

metric_info["k8s_pods_request"] = {
    "title": _("Pods"),
    "unit": "count",
    "color": "16/b",
}

metric_info["k8s_pods_allocatable"] = {
    "title": _("Allocatable"),
    "unit": "count",
    "color": "#e0e0e0",
}

metric_info["k8s_pods_capacity"] = {
    "title": _("Capacity"),
    "unit": "count",
    "color": "#c0c0c0",
}

metric_info["k8s_pods_pending"] = {"title": _("Pending"), "unit": "count", "color": "#d1d4e8"}

metric_info["k8s_pods_running"] = {
    "title": _("Running"),
    "unit": "count",
    "color": "#93a2ee",
}

metric_info["k8s_cpu_request"] = {
    "title": _("Request"),
    "unit": "",
    "color": "26/b",
}

metric_info["k8s_cpu_limit"] = {
    "title": _("Limit"),
    "unit": "",
    "color": "26/a",
}

metric_info["k8s_cpu_allocatable"] = {
    "title": _("Allocatable"),
    "unit": "",
    "color": "#e0e0e0",
}

metric_info["k8s_cpu_capacity"] = {
    "title": _("Capacity"),
    "unit": "",
    "color": "#c0c0c0",
}

metric_info["k8s_memory_request"] = {
    "title": _("Request"),
    "unit": "bytes",
    "color": "42/b",
}


metric_info["k8s_memory_requests"] = {
    "title": _("Request"),
    "unit": "bytes",
    "color": "42/b",
}

metric_info["k8s_memory_limit"] = {
    "title": _("Limit"),
    "unit": "bytes",
    "color": "42/a",
}

metric_info["k8s_memory_allocatable"] = {
    "title": _("Allocatable"),
    "unit": "bytes",
    "color": "#e0e0e0",
}

metric_info["k8s_memory_capacity"] = {
    "title": _("Capacity"),
    "unit": "bytes",
    "color": "#c0c0c0",
}

metric_info["k8s_pods_usage"] = {
    "title": _("Pod request"),
    "unit": "%",
    "color": "31/a",
}

metric_info["k8s_memory_usage"] = {
    "title": _("Memory request"),
    "unit": "%",
    "color": "31/a",
}


metric_info["k8s_mem_used"] = {
    "color": "#80ff40",
    "title": _("Memory used"),
    "unit": "bytes",
}


metric_info["k8s_mem_used_percent"] = {
    "color": "#80ff40",
    "title": _("Memory used %"),
    "unit": "%",
}


metric_info["k8s_cpu_usage"] = {
    "title": _("CPU request"),
    "unit": "%",
    "color": "31/a",
}

metric_info["k8s_total_roles"] = {
    "title": _("Total"),
    "unit": "",
    "color": "31/a",
}

metric_info["k8s_cluster_roles"] = {
    "title": _("Cluster roles"),
    "unit": "",
    "color": "21/a",
}

metric_info["k8s_roles"] = {
    "title": _("Roles"),
    "unit": "",
    "color": "21/b",
}

metric_info["k8s_daemon_pods_ready"] = {
    "title": _("Number of nodes ready"),
    "unit": "",
    "color": "23/a",
}

metric_info["k8s_daemon_pods_scheduled_desired"] = {
    "title": _("Desired number of nodes scheduled"),
    "unit": "",
    "color": "21/a",
}

metric_info["k8s_daemon_pods_scheduled_current"] = {
    "title": _("Current number of nodes scheduled"),
    "unit": "",
    "color": "31/a",
}

metric_info["k8s_daemon_pods_scheduled_updated"] = {
    "title": _("Number of nodes scheduled with up-to-date pods"),
    "unit": "",
    "color": "22/a",
}

metric_info["k8s_daemon_pods_available"] = {
    "title": _("Number of nodes scheduled with available pods"),
    "unit": "",
    "color": "35/a",
}

metric_info["k8s_daemon_pods_unavailable"] = {
    "title": _("Number of nodes scheduled with unavailable pods"),
    "unit": "",
    "color": "14/a",
}

metric_info["ready_replicas"] = {
    "title": _("Ready replicas"),
    "unit": "",
    "color": "21/a",
}

metric_info["total_replicas"] = {
    "title": _("Total replicas"),
    "unit": "",
    "color": "35/a",
}


# .
#   .--Graphs--------------------------------------------------------------.
#   |                    ____                 _                            |
#   |                   / ___|_ __ __ _ _ __ | |__  ___                    |
#   |                  | |  _| '__/ _` | '_ \| '_ \/ __|                   |
#   |                  | |_| | | | (_| | |_) | | | \__ \                   |
#   |                   \____|_|  \__,_| .__/|_| |_|___/                   |
#   |                                  |_|                                 |
#   +----------------------------------------------------------------------+
#   |  Definitions of time series graphs                                   |
#   '----------------------------------------------------------------------'

graph_info["k8s_resources.pods"] = {
    "title": _("Pod resources"),
    "metrics": [
        ("k8s_pods_capacity", "area"),
        ("k8s_pods_allocatable", "area"),
        ("k8s_pods_request", "area"),
    ],
}

graph_info["k8s_resources.pod"] = {
    "title": _("Pod resources"),
    "metrics": [
        ("k8s_pods_allocatable", "line"),
        ("k8s_pods_capacity", "line"),
        ("k8s_pods_running", "area"),
        ("k8s_pods_pending", "stack"),
    ],
}

graph_info["k8s_resources.cpu"] = {
    "title": _("CPU resources"),
    "metrics": [
        ("k8s_cpu_capacity", "area"),
        ("k8s_cpu_allocatable", "area"),
        ("k8s_cpu_limit", "area"),
        ("k8s_cpu_request", "area"),
    ],
    "optional_metrics": ["k8s_cpu_capacity", "k8s_cpu_allocatable", "k8s_cpu_limit"],
}

graph_info["k8s_resources.memory"] = {
    "title": _("Memory resources"),
    "metrics": [
        ("k8s_memory_capacity", "area"),
        ("k8s_memory_allocatable", "area"),
        ("k8s_memory_limit", "area"),
        ("k8s_memory_request", "area"),
    ],
    "optional_metrics": ["k8s_memory_capacity", "k8s_memory_allocatable", "k8s_memory_limit"],
}


graph_info["k8s_memory_usage"] = {
    "title": _("Memory usage"),
    "metrics": [
        ("k8s_memory_requests", "line"),
        ("k8s_memory_limit", "line"),
        ("k8s_mem_used", "area"),
    ],
    "optional_metrics": ["k8s_memory_request", "k8s_memory_limit"],
}


graph_info["k8s_pod_container"] = {
    "title": _("Ready containers"),
    "metrics": [
        ("docker_all_containers", "line"),
        ("ready_containers", "area"),
    ],
}


graph_info["replicas"] = {
    "title": _("Replicas"),
    "metrics": [
        ("ready_replicas", "area"),
        ("total_replicas", "line"),
    ],
    "scalars": [
        "ready_replicas:crit",
    ],
}
