#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing._utils import graph_info, metric_info
from cmk.gui.i18n import _

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

metric_info["streams"] = {
    "title": _("Streams"),
    "unit": "%",
    "color": "35/a",
}

# cloud storage

metric_info["mem_growth"] = {
    "title": _("Memory usage growth"),
    "unit": "bytes/d",
    "color": "#29cfaa",
}

metric_info["capacity_perc"] = {
    "title": _("Available capacity"),
    "unit": "%",
    "color": "#4800ff",
}

metric_info["log_file_utilization"] = {
    "title": _("Percentage of log file used"),
    "unit": "%",
    "color": "42/a",
}

metric_info["io_consumption_percent"] = {
    "title": _("Storage IO consumption"),
    "unit": "%",
    "color": "25/b",
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

# diskstat checks

graph_info["ram_swap_used"] = {
    "title": _("RAM + Swap used"),
    "metrics": [
        ("mem_used", "stack"),
        ("swap_used", "stack"),
    ],
    "conflicting_metrics": ["swap_total"],
    "scalars": [
        ("swap_used:max,mem_used:max,+#008080", _("Total RAM + Swap installed")),
        ("mem_used:max#80ffff", _("Total RAM installed")),
    ],
    "range": (0, "swap_used:max,mem_used:max,+"),
}

graph_info["mem_growing"] = {
    "title": _("Growing"),
    "metrics": [
        (
            "mem_growth.max,0,MAX",
            "area",
            _("Growth"),
        ),
    ],
}

graph_info["mem_shrinking"] = {
    "title": _("Shrinking"),
    "consolidation_function": "min",
    "metrics": [
        ("mem_growth.min,0,MIN,-1,*#299dcf", "-area", _("Shrinkage")),
    ],
}

# Linux memory graphs. They are a lot...

graph_info["ram_swap_overview"] = {
    "title": _("RAM + swap overview"),
    "metrics": [
        ("mem_total,swap_total,+#87cefa", "area", _("RAM + swap installed")),
        ("mem_used,swap_used,+#37fa37", "line", _("RAM + swap used")),
    ],
}

graph_info["swap"] = {
    "title": _("Swap"),
    "metrics": [
        ("swap_total", "line"),
        ("swap_used", "stack"),
        ("swap_cached", "stack"),
    ],
}

graph_info["ram_used"] = {
    "title": _("RAM used"),
    "metrics": [
        ("mem_used", "area"),
    ],
    "conflicting_metrics": ["swap_used"],
    "scalars": [
        ("mem_used:max#000000", "Maximum"),
        ("mem_used:warn", "Warning"),
        ("mem_used:crit", "Critical"),
    ],
    "range": (0, "mem_used:max"),
}
