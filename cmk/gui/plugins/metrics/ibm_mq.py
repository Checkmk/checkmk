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

metric_info["curdepth"] = {
    "title": _("Queue depth"),
    "help": _(
        "The current depth of the queue, that is, the number of messages "
        "on the queue, including both committed messages and uncommitted messages."
    ),
    "unit": "count",
    "color": "#4287f5",
}

metric_info["msgage"] = {
    "title": _("Age of oldest message"),
    "help": _("Age, in seconds, of the oldest message on the queue."),
    "unit": "s",
    "color": "#4287f5",
}

metric_info["ipprocs"] = {
    "title": _("Open input handles"),
    "help": _("Number of handles that are currently open for input for the queue."),
    "unit": "count",
    "color": "#0da317",
}

metric_info["opprocs"] = {
    "title": _("Open output handles"),
    "help": _("Number of handles that are currently open for output for the queue."),
    "unit": "count",
    "color": "#4287f5",
}

metric_info["qtime_short"] = {
    "title": _("Queue time short"),
    "help": _("Mean time in queue for the last few messages."),
    "unit": "s",
    "color": "#4287f5",
}

metric_info["qtime_long"] = {
    "title": _("Queue time long"),
    "help": _("Mean time in queue for the last medium number of messages."),
    "unit": "s",
    "color": "#0da317",
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

graph_info["ibm_mq_queue_procs"] = {
    "title": _("Open input/output handles"),
    "metrics": [
        ("ipprocs", "line"),
        ("opprocs", "line"),
    ],
}

graph_info["ibm_mq_qtime"] = {
    "title": _("Average time messages stay on queue"),
    "metrics": [
        ("qtime_short", "line"),
        ("qtime_long", "line"),
    ],
}
