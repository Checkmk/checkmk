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

metric_info["call_legs"] = {
    "title": _l("Call legs"),
    "unit": "count",
    "color": "#60bbbb",
}

metric_info["database_apply_lag"] = {
    "title": _l("Database apply lag"),
    "help": _l(
        "Amount of time that the application of redo data on the standby database lags behind the primary database"
    ),
    "unit": "s",
    "color": "#006040",
}

metric_info["replication_lag"] = {
    "title": _l("Replication lag"),
    "help": _l("Amount of time that the replica server is lagging against the source server"),
    "unit": "s",
    "color": "14/a",
}

metric_info["active_vms"] = {
    "title": _l("Active VMs"),
    "unit": "count",
    "color": "14/a",
}

metric_info["quarantine"] = {
    "title": _l("Quarantine Usage"),
    "unit": "%",
    "color": "43/b",
}

metric_info["elapsed_time"] = {
    "title": _l("Elapsed time"),
    "unit": "s",
    "color": "11/a",
}

metric_info["items_count"] = {
    "title": _l("Items"),
    "unit": "count",
    "color": "23/a",
}

metric_info["num_user"] = {
    "title": _l("User"),
    "unit": "count",
    "color": "23/a",
}

metric_info["max_user"] = {
    "title": _l("Maximum allowed users"),
    "unit": "count",
    "color": "25/a",
}

# DRBD metrics
metric_info["memory_reservation"] = {
    "title": _l("Memory reservation"),
    "unit": "%",
    "color": "36/a",
}

metric_info["sms_success_rate"] = {
    "title": _l("SMS success rate"),
    "unit": "%",
    "color": "35/a",
}

metric_info["cpu_credits_consumed"] = {
    "title": _l("Credits consumed"),
    "unit": "count",
    "color": "15/a",
}

metric_info["cpu_credits_remaining"] = {
    "title": _l("Credits remaining"),
    "unit": "count",
    "color": "11/a",
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

graph_info["current_users"] = {
    "title": _l("Number of signed-in users"),
    "metrics": [
        ("current_users", "area"),
    ],
    "scalars": [
        "current_users:warn",
        "current_users:crit",
    ],
}


graph_info["firewall_users"] = {
    "title": _l("Number of active users"),
    "metrics": [
        ("num_user", "line"),
        ("max_user", "line"),
    ],
}

graph_info["cpu_credits"] = {
    "title": _l("CPU credits"),
    "metrics": [
        ("cpu_credits_consumed", "line"),
        ("cpu_credits_remaining", "line"),
    ],
}
