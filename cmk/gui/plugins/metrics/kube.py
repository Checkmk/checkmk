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

requirement_to_utilization_titles = {
    "request": _("Requests utilization"),
    "limit": _("Limits utilization"),
    "cluster_allocatable": _("Cluster utilization"),
    "node_allocatable": _("Node utilization"),
}
requirement_to_absolute_titles = {
    "request": _("Requests"),
    "limit": _("Limits"),
    "allocatable": _("Allocatable"),
}

requirement_colors = {
    "request": "42/a",
    "limit": "42/b",
    "allocatable": "46/a",
    "cluster_allocatable": "46/a",
    "node_allocatable": "46/a",
}

for resource, usage_unit in zip(["memory", "cpu"], ["bytes", ""]):
    metric_info[f"kube_{resource}_usage"] = {
        "title": _("Usage"),
        "unit": usage_unit,
        "color": "31/a",
    }
    for req, title in requirement_to_absolute_titles.items():
        metric_info[f"kube_{resource}_{req}"] = {
            "title": title,
            "unit": usage_unit,
            "color": requirement_colors[req],
        }
    for req, title in requirement_to_utilization_titles.items():
        metric_info[f"kube_{resource}_{req}_utilization"] = {
            "title": title,
            "unit": "%",
            "color": requirement_colors[req],
        }

metric_info["kube_node_count_worker_ready"] = {
    "title": _("Worker nodes ready"),
    "unit": "count",
    "color": "14/a",
}

metric_info["kube_node_count_worker_not_ready"] = {
    "title": _("Worker nodes not ready"),
    "unit": "count",
    "color": "14/b",
}

metric_info["kube_node_count_worker_total"] = {
    "title": _("Worker nodes total"),
    "unit": "count",
    "color": "51/a",
}

metric_info["kube_node_count_control_plane_ready"] = {
    "title": _("Control plane nodes ready"),
    "unit": "count",
    "color": "42/a",
}

metric_info["kube_node_count_control_plane_not_ready"] = {
    "title": _("Control plane nodes not ready"),
    "unit": "count",
    "color": "42/b",
}

metric_info["kube_node_count_control_plane_total"] = {
    "title": _("Control plane nodes total"),
    "unit": "count",
    "color": "51/a",
}


metric_info["kube_pod_restart_count"] = {
    "title": _("Restarts"),
    "unit": "",
    "color": "42/a",
}

metric_info["kube_pod_restart_rate"] = {
    "title": _("Restarts per hour"),
    "unit": "",
    "color": "42/b",
}

metric_info["kube_desired_replicas"] = {
    "title": _("Desired replicas"),
    "unit": "count",
    "color": "41/a",
}

metric_info["kube_ready_replicas"] = {
    "title": _("Ready replicas"),
    "unit": "count",
    "color": "21/a",
}

metric_info["kube_updated_replicas"] = {
    "title": _("Up-to-date replicas"),
    "unit": "count",
    "color": "31/a",
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
    "optional_metrics": ["kube_pod_free", "kube_pod_allocatable"],
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

for resource, usage_title in zip(["memory", "cpu"], [_("Memory"), _("CPU")]):
    graph_info[f"kube_{resource}_usage"] = {
        "title": usage_title,
        "metrics": [
            (f"kube_{resource}_request", "line"),
            (f"kube_{resource}_limit", "line"),
            (f"kube_{resource}_usage", "area"),
            (f"kube_{resource}_allocatable", "line"),
        ],
        "optional_metrics": [
            f"kube_{resource}_request",
            f"kube_{resource}_limit",
            f"kube_{resource}_usage",
            f"kube_{resource}_allocatable",
        ],
        "scalars": [
            f"kube_{resource}_usage:warn",
            f"kube_{resource}_usage:crit",
        ],
    }

graph_info["kube_node_count_worker"] = {
    "title": _("Worker nodes"),
    "metrics": [
        ("kube_node_count_worker_ready", "stack"),
        ("kube_node_count_worker_not_ready", "stack"),
        ("kube_node_count_worker_total", "line"),
    ],
}

graph_info["kube_node_count_control_plane"] = {
    "title": _("Control plane nodes"),
    "metrics": [
        ("kube_node_count_control_plane_ready", "stack"),
        ("kube_node_count_control_plane_not_ready", "stack"),
        ("kube_node_count_control_plane_total", "line"),
    ],
}

graph_info["kube_pod_restarts"] = {
    "title": _("Pod Restarts"),
    "metrics": [
        ("kube_pod_restart_count", "line"),
        ("kube_pod_restart_rate", "line"),
    ],
    "optional_metrics": [
        "kube_pod_restart_rate",
    ],
}


graph_info["kube_replica_state"] = {
    "title": _("Replica state"),
    "metrics": [
        ("kube_desired_replicas", "area"),
        ("kube_ready_replicas", "line"),
    ],
}


graph_info["kube_replica_update_state"] = {
    "title": _("Replica update state"),
    "metrics": [
        ("kube_desired_replicas", "area"),
        ("kube_updated_replicas", "line"),
    ],
}
