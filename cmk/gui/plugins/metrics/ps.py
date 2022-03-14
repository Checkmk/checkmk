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

metric_info["process_creations"] = {
    "title": _("Process creations"),
    "unit": "1/s",
    "color": "#ff8020",
}

metric_info["process_virtual_size"] = {
    "title": _("Virtual size"),
    "unit": "bytes",
    "color": "16/a",
}

metric_info["process_resident_size"] = {
    "title": _("Resident size"),
    "unit": "bytes",
    "color": "14/a",
}

metric_info["process_mapped_size"] = {
    "title": _("Mapped size"),
    "unit": "bytes",
    "color": "12/a",
}

metric_info["process_handles"] = {
    "title": _("Process handles"),
    "unit": "count",
    "color": "32/a",
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

# For the 'ps' check there are multiple graphs.
# Without the graph info 'number_of_processes', the graph will not show,
# because 'size_per_process' uses the variable name 'processes' as well.
# Once a variable is used by some other graph it will not create a single graph anymore.
# That is why we have to define a specific graph info here.
# Further details see here: metrics/utils.py -> _get_implicit_graph_templates()
graph_info["number_of_processes"] = {
    "title": _("Number of processes"),
    "metrics": [
        ("processes", "area"),
    ],
}

graph_info["size_of_processes"] = {
    "title": _("Size of processes"),
    "metrics": [
        ("process_virtual_size", "stack"),
        ("process_mapped_size", "stack"),
        ("process_resident_size", "area"),
    ],
    "optional_metrics": ["process_mapped_size"],
}

graph_info["size_per_process"] = {
    "title": _("Size per process"),
    "metrics": [
        ("process_resident_size,processes,/", "area", _("Average resident size per process")),
        ("process_virtual_size,processes,/", "stack", _("Average virtual size per process")),
    ],
}
