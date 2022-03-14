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

metric_info["jenkins_job_score"] = {
    "title": _("Job score"),
    "unit": "%",
    "color": "11/a",
}

metric_info["jenkins_time_since"] = {
    "title": _("Time since last successful build"),
    "unit": "s",
    "color": "21/a",
}

metric_info["jenkins_build_duration"] = {
    "title": _("Build duration"),
    "unit": "s",
    "color": "31/a",
}

metric_info["jenkins_num_executors"] = {
    "title": _("Total number of executors"),
    "unit": "count",
    "color": "25/a",
}

metric_info["jenkins_busy_executors"] = {
    "title": _("Number of busy executors"),
    "unit": "count",
    "color": "11/b",
}

metric_info["jenkins_idle_executors"] = {
    "title": _("Number of idle executors"),
    "unit": "count",
    "color": "23/a",
}

metric_info["jenkins_clock"] = {
    "title": _("Clock difference"),
    "unit": "s",
    "color": "25/a",
}

metric_info["jenkins_temp"] = {
    "title": _("Available temp space"),
    "unit": "bytes",
    "color": "53/a",
}

metric_info["jenkins_stuck_tasks"] = {
    "title": _("Number of stuck tasks"),
    "unit": "count",
    "color": "11/a",
}

metric_info["jenkins_blocked_tasks"] = {
    "title": _("Number of blocked tasks"),
    "unit": "count",
    "color": "31/a",
}

metric_info["jenkins_pending_tasks"] = {
    "title": _("Number of pending tasks"),
    "unit": "count",
    "color": "51/a",
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

graph_info["number_of_executors"] = {
    "title": _("Executors"),
    "metrics": [
        ("jenkins_num_executors", "area"),
        ("jenkins_busy_executors", "area"),
        ("jenkins_idle_executors", "area"),
    ],
}

graph_info["number_of_tasks"] = {
    "title": _("Tasks"),
    "metrics": [
        ("jenkins_stuck_tasks", "area"),
        ("jenkins_blocked_tasks", "area"),
        ("jenkins_pending_tasks", "area"),
    ],
}
