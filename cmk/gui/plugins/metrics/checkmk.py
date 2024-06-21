#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing._utils import graph_info, metric_info
from cmk.gui.i18n import _l

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

metric_info["hosts_active"] = {
    "title": _l("Active hosts"),
    "unit": "count",
    "color": "11/a",
}

metric_info["hosts_inactive"] = {
    "title": _l("Inactive hosts"),
    "unit": "count",
    "color": "16/a",
}

metric_info["hosts_degraded"] = {
    "title": _l("Degraded hosts"),
    "unit": "count",
    "color": "23/a",
}

metric_info["hosts_offline"] = {
    "title": _l("Offline hosts"),
    "unit": "count",
    "color": "31/a",
}

metric_info["hosts_other"] = {
    "title": _l("Other hosts"),
    "unit": "count",
    "color": "41/a",
}

metric_info["hosts_healthy"] = {
    "title": _l("Healthy hosts"),
    "unit": "count",
    "color": "46/a",
}

metric_info["helper_usage_cmk"] = {
    "title": _l("Checkmk helper usage"),
    "unit": "%",
    "color": "15/a",
}

metric_info["cmk_time_agent"] = {
    "title": _l("Time spent waiting for Checkmk agent"),
    "unit": "s",
    "color": "36/a",
}

metric_info["cmk_time_snmp"] = {
    "title": _l("Time spent waiting for SNMP responses"),
    "unit": "s",
    "color": "32/a",
}

metric_info["cmk_time_ds"] = {
    "title": _l("Time spent waiting for special agent"),
    "unit": "s",
    "color": "34/a",
}

metric_info["normal_updates"] = {
    "title": _l("Pending normal updates"),
    "unit": "count",
    "color": "#c08030",
}

metric_info["security_updates"] = {
    "title": _l("Pending security updates"),
    "unit": "count",
    "color": "#ff0030",
}

metric_info["num_high_alerts"] = {
    "title": _l("High alerts"),
    "unit": "count",
    "color": "22/a",
}

metric_info["num_disabled_alerts"] = {
    "title": _l("Disabled alerts"),
    "unit": "count",
    "color": "24/a",
}

metric_info["age_oldest"] = {
    "title": _l("Oldest age"),
    "unit": "s",
    "color": "35/a",
}

metric_info["age_youngest"] = {
    "title": _l("Youngest age"),
    "unit": "s",
    "color": "21/a",
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

graph_info["helper_usage_cmk"] = {
    "title": _l("Checkmk helper usage"),
    "metrics": [
        ("helper_usage_cmk", "area"),
    ],
    "range": (0, 100),
}

graph_info["pending_updates"] = {
    "title": _l("Pending updates"),
    "metrics": [
        ("normal_updates", "stack"),
        ("security_updates", "stack"),
    ],
}
