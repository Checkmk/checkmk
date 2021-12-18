#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.metrics.utils import graph_info, metric_info

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

metric_info["kube_pod_allocatable"] = {
    "title": _("Allocatable"),
    "unit": "count",
    "color": "35/b",
}

metric_info["kube_pod_pending"] = {
    "title": _("Pending"),
    "unit": "count",
    "color": "13/b",
}

metric_info["kube_pod_running"] = {
    "title": _("Running"),
    "unit": "count",
    "color": "31/a",
}

metric_info["kube_pod_free"] = {
    "title": _("Free"),
    "unit": "count",
    "color": "51/a",
}

metric_info["kube_pod_failed"] = {
    "title": _("Failed"),
    "unit": "count",
    "color": "22/a",
}

metric_info["kube_pod_succeeded"] = {
    "title": _("Succeeded"),
    "unit": "count",
    "color": "46/a",
}

metric_info["kube_node_container_count_running"] = {
    "title": _("Running containers"),
    "unit": "count",
    "color": "35/a",
}

metric_info["kube_node_container_count_waiting"] = {
    "title": _("Waiting containers"),
    "unit": "count",
    "color": "22/a",
}

metric_info["kube_node_container_count_terminated"] = {
    "title": _("Terminated containers"),
    "unit": "count",
    "color": "15/a",
}

metric_info["kube_node_container_count_total"] = {
    "title": _("Total containers"),
    "unit": "count",
    "color": "42/a",
}

metric_info["kube_cpu_usage"] = {
    "title": _("Usage"),
    "unit": "",
    "color": "31/a",
}

metric_info["kube_cpu_request"] = {
    "title": _("Request"),
    "unit": "",
    "color": "42/a",
}

metric_info["kube_cpu_limit"] = {
    "title": _("Limit"),
    "unit": "",
    "color": "42/b",
}

metric_info["kube_cpu_request_utilization"] = {
    "title": _("Request utilization"),
    "unit": "%",
    "color": "22/a",
}

metric_info["kube_cpu_limit_utilization"] = {
    "title": _("Limit utilization"),
    "unit": "%",
    "color": "46/a",
}

metric_info["kube_memory_usage"] = {
    "title": _("Usage"),
    "unit": "bytes",
    "color": "31/a",
}

metric_info["kube_memory_request"] = {
    "title": _("Request"),
    "unit": "bytes",
    "color": "42/a",
}

metric_info["kube_memory_limit"] = {
    "title": _("Limit"),
    "unit": "bytes",
    "color": "42/b",
}


metric_info["kube_memory_request_utilization"] = {
    "title": _("Request utilization"),
    "unit": "%",
    "color": "42/a",
}

metric_info["kube_memory_limit_utilization"] = {
    "title": _("Limit utilization"),
    "unit": "%",
    "color": "42/b",
}

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


graph_info["kube_pod_resources"] = {
    "title": _("Allocated pod resources"),
    "metrics": [
        ("kube_pod_running", "area"),
        ("kube_pod_pending", "stack"),
        ("kube_pod_free", "stack"),
        ("kube_pod_allocatable", "line"),
    ],
    "optional_metrics": ["kube_pod_allocatable", "kube_pod_free"],
}

graph_info["kube_resources_terminated"] = {
    "title": _("Terminated pod resources"),
    "metrics": [
        ("kube_pod_succeeded", "line"),
        ("kube_pod_failed", "line"),
    ],
}

graph_info["kube_node_container_count"] = {
    "title": _("Containers"),
    "metrics": [
        ("kube_node_container_count_running", "stack"),
        ("kube_node_container_count_waiting", "stack"),
        ("kube_node_container_count_terminated", "stack"),
        ("kube_node_container_count_total", "line"),
    ],
    "scalars": [
        "kube_node_container_count_total:warn",
        "kube_node_container_count_total:crit",
    ],
}

graph_info["kube_cpu_usage"] = {
    "title": _("CPU"),
    "metrics": [
        ("kube_cpu_request", "line"),
        ("kube_cpu_limit", "line"),
        ("kube_cpu_usage", "area"),
    ],
    "optional_metrics": ["kube_cpu_request", "kube_cpu_limit"],
}

graph_info["kube_cpu_utilization"] = {
    "title": _("CPU Utilization"),
    "metrics": [
        ("kube_cpu_request_utilization", "line"),
        ("kube_cpu_limit_utilization", "line"),
    ],
    "optional_metrics": ["kube_cpu_request_utilization", "kube_cpu_limit_utilization"],
}

# TODO Add additional boundaries for percent. (only zero at the bottom)
graph_info["kube_memory_usage"] = {
    "title": _("Container memory"),
    "metrics": [
        ("kube_memory_request", "line"),
        ("kube_memory_limit", "line"),
        ("kube_memory_usage", "area"),
    ],
    "optional_metrics": ["kube_memory_request", "kube_memory_limit"],
}

graph_info["kube_memory_utilization"] = {
    "title": _("Memory utilization"),
    "metrics": [
        ("kube_memory_request_utilization", "line"),
        ("kube_memory_limit_utilization", "line"),
    ],
    "optional_metrics": ["kube_memory_request_utilization", "kube_memory_limit_utilization"],
}
