#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _l
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

metric_info["omd_log_size"] = {
    "title": _l("Size of log files"),
    "unit": "bytes",
    "color": "11/a",
}
metric_info["omd_rrd_size"] = {
    "title": _l("Size of RRDs"),
    "unit": "bytes",
    "color": "21/a",
}
metric_info["omd_size"] = {
    "title": _l("Total size of site"),
    "unit": "bytes",
    "color": "31/a",
}

graph_info["omd_fileusage"] = {
    "title": _l("OMD filesystem usage"),
    "metrics": [
        ("omd_log_size", "stack"),
        ("omd_rrd_size", "stack"),
        ("omd_size", "line"),
    ],
}
