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

metric_info["fs_free"] = {
    "title": _("Free filesystem space"),
    "unit": "bytes",
    "color": "#e3fff9",
}

metric_info["reserved"] = {
    "title": _("Reserved filesystem space"),
    "unit": "bytes",
    "color": "#ffcce6",
}

metric_info["fs_used"] = {
    "title": _("Used filesystem space"),
    "unit": "bytes",
    "color": "#00ffc6",
}

metric_info["fs_used_percent"] = {
    "title": _("Used filesystem space %"),
    "unit": "%",
    "color": "#00ffc6",
}

metric_info["fs_size"] = {
    "title": _("Filesystem size"),
    "unit": "bytes",
    "color": "#006040",
}

metric_info["fs_growth"] = {
    "title": _("Filesystem growth"),
    "unit": "bytes/d",
    "color": "#29cfaa",
}

metric_info["fs_trend"] = {
    "title": _("Trend of filesystem growth"),
    "unit": "bytes/d",
    "color": "#808080",
}

metric_info["fs_provisioning"] = {
    "title": _("Provisioned filesystem space"),
    "unit": "bytes",
    "color": "#ff8000",
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

graph_info["fs_used"] = {
    "title": _("Filesystem size and used space"),
    "metrics": [
        ("fs_used", "area"),
        ("fs_size,fs_used,-#e3fff9", "stack", _("Free space")),
        ("fs_size", "line"),
    ],
    "scalars": [
        "fs_used:warn",
        "fs_used:crit",
    ],
    "range": (0, "fs_used:max"),
    "conflicting_metrics": ["fs_free"],
}

# draw a different graph if space reserved for root was excluded
graph_info["fs_used_2"] = {
    "title": _("Filesystem size and usage"),
    "metrics": [
        ("fs_used", "area"),
        ("fs_free", "stack"),
        ("reserved", "stack"),
        ("fs_size", "line"),
    ],
    "scalars": [
        "fs_used:warn",
        "fs_used:crit",
    ],
    "range": (0, "fs_used:max"),
}

graph_info["growing"] = {
    "title": _("Growing"),
    "metrics": [
        (
            "fs_growth.max,0,MAX",
            "area",
            _("Growth"),
        ),
    ],
}

graph_info["shrinking"] = {
    "title": _("Shrinking"),
    "consolidation_function": "min",
    "metrics": [
        ("fs_growth.min,0,MIN,-1,*#299dcf", "-area", _("Shrinkage")),
    ],
}

graph_info["fs_trend"] = {
    "title": _("Trend of filesystem growth"),
    "metrics": [
        ("fs_trend", "line"),
    ],
}
