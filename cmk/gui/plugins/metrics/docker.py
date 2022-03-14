#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.metrics.utils import graph_info, metric_info

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

metric_info["docker_all_containers"] = {
    "title": _("Number of containers"),
    "unit": "count",
    "color": "43/a",
}

metric_info["docker_running_containers"] = {
    "title": _("Running containers"),
    "unit": "count",
    "color": "31/a",
}

metric_info["ready_containers"] = {
    "title": _("Ready containers"),
    "unit": "count",
    "color": "23/a",
}

metric_info["docker_paused_containers"] = {
    "title": _("Paused containers"),
    "unit": "count",
    "color": "24/a",
}

metric_info["docker_stopped_containers"] = {
    "title": _("Stopped containers"),
    "unit": "count",
    "color": "14/a",
}

metric_info["docker_count"] = {
    "title": _("Count"),
    "unit": "count",
    "color": "11/a",
}

metric_info["docker_active"] = {
    "title": _("Active"),
    "unit": "count",
    "color": "21/a",
}

metric_info["docker_size"] = {
    "title": _("Size"),
    "unit": "bytes",
    "color": "41/a",
}

metric_info["docker_reclaimable"] = {
    "title": _("Reclaimable"),
    "unit": "bytes",
    "color": "31/a",
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

graph_info["docker_containers"] = {
    "title": _("Docker Containers"),
    "metrics": [
        ("docker_running_containers", "area"),
        ("docker_paused_containers", "stack"),
        ("docker_stopped_containers", "stack"),
        ("docker_all_containers", "line"),
    ],
}

graph_info["docker_df"] = {
    "title": _("Docker Disk Usage"),
    "metrics": [
        ("docker_size", "area"),
        ("docker_reclaimable", "area"),
    ],
}

graph_info["docker_df_count"] = {
    "title": _("Docker Disk Usage Count"),
    "metrics": [
        ("docker_count", "area"),
        ("docker_active", "area"),
    ],
}
