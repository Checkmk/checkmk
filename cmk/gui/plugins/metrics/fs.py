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

metric_info["fs_free"] = {
    "title": _("Free space"),
    "unit": "bytes",
    "color": "#e3fff9",
}

metric_info["reserved"] = {
    "title": _("Reserved space"),
    "unit": "bytes",
    "color": "#ffcce6",
}

metric_info["fs_used"] = {
    "title": _("Used space"),
    "unit": "bytes",
    "color": "#00ffc6",
}

metric_info["fs_used_percent"] = {
    "title": _("Used space %"),
    "unit": "%",
    "color": "#00ffc6",
}

metric_info["fs_size"] = {
    "title": _("Total size"),
    "unit": "bytes",
    "color": "#006040",
}

metric_info["fs_growth"] = {
    "title": _("Growth"),
    "unit": "bytes/d",
    "color": "#29cfaa",
}

metric_info["fs_trend"] = {
    "title": _("Growth trend"),
    "unit": "bytes/d",
    "color": "#808080",
}

metric_info["fs_provisioning"] = {
    "title": _("Provisioned space"),
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
    "title": _("Size and used space"),
    "metrics": [
        # NOTE: in this scenario, fs_used includes reserved space
        ("fs_used", "area"),
        ("fs_size,fs_used,-#e3fff9", "stack", _("Free space")),  # this has to
        # remain a calculated value for compatibility reasons: fs_free has not
        # always been available as a metric (see CMK-12488)
        ("fs_size", "line"),
    ],
    "scalars": [
        "fs_used:warn",
        "fs_used:crit",
    ],
    "range": (0, "fs_used:max"),
    "conflicting_metrics": ["reserved"],
}

# draw a different graph if space reserved for root was excluded
graph_info["fs_used_2"] = {
    "title": _("Size and used space"),
    "metrics": [
        ("fs_used", "area"),
        ("fs_free", "stack"),
        ("reserved", "stack"),
        ("fs_used,fs_free,reserved,+,+#006040", "line", _("Filesystem size")),
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
    "title": _("Growth trend"),
    "metrics": [
        ("fs_trend", "line"),
    ],
}
