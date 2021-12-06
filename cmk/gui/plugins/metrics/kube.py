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
