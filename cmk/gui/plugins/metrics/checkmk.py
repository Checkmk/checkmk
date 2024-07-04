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

metric_info["helper_usage_cmk"] = {
    "title": _l("Checkmk helper usage"),
    "unit": "%",
    "color": "15/a",
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
