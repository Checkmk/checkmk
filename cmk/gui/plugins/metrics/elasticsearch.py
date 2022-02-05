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

metric_info["elasticsearch_size_avg"] = {
    "title": _("Average size growth"),
    "unit": "bytes",
    "color": "33/a",
}

metric_info["elasticsearch_size_rate"] = {
    "title": _("Size growth per minute"),
    "unit": "bytes",
    "color": "31/a",
}

metric_info["elasticsearch_size"] = {
    "title": _("Total size"),
    "unit": "bytes",
    "color": "31/b",
}

metric_info["elasticsearch_count_avg"] = {
    "title": _("Average document count growth"),
    "unit": "count",
    "color": "45/a",
}

metric_info["elasticsearch_count_rate"] = {
    "title": _("Document count growth per minute"),
    "unit": "count",
    "color": "43/a",
}

metric_info["elasticsearch_count"] = {
    "title": _("Total documents"),
    "unit": "count",
    "color": "43/b",
}

metric_info["active_primary_shards"] = {
    "title": _("Active primary shards"),
    "unit": "count",
    "color": "21/b",
}

metric_info["active_shards"] = {
    "title": _("Active shards"),
    "unit": "count",
    "color": "21/a",
}

metric_info["active_shards_percent_as_number"] = {
    "title": _("Active shards in percent"),
    "unit": "%",
    "color": "22/a",
}

metric_info["number_of_data_nodes"] = {
    "title": _("Data nodes"),
    "unit": "count",
    "color": "41/a",
}

metric_info["delayed_unassigned_shards"] = {
    "title": _("Delayed unassigned shards"),
    "unit": "count",
    "color": "42/a",
}

metric_info["initializing_shards"] = {
    "title": _("Initializing shards"),
    "unit": "count",
    "color": "52/a",
}

metric_info["number_of_nodes"] = {
    "title": _("Nodes"),
    "unit": "count",
    "color": "43/a",
}

metric_info["number_of_pending_tasks"] = {
    "title": _("Pending tasks"),
    "unit": "count",
    "color": "53/a",
}

metric_info["number_of_pending_tasks_rate"] = {
    "title": _("Pending tasks delta"),
    "unit": "count",
    "color": "14/b",
}

metric_info["number_of_pending_tasks_avg"] = {
    "title": _("Average pending tasks delta"),
    "unit": "count",
    "color": "26/a",
}

metric_info["relocating_shards"] = {
    "title": _("Relocating shards"),
    "unit": "count",
    "color": "16/b",
}

metric_info["task_max_waiting_in_queue_millis"] = {
    "title": _("Maximum wait time of all tasks in queue"),
    "unit": "count",
    "color": "11/a",
}

metric_info["unassigned_shards"] = {
    "title": _("Unassigned shards"),
    "unit": "count",
    "color": "14/a",
}

metric_info["number_of_in_flight_fetch"] = {
    "title": _("Ongoing shard info requests"),
    "unit": "count",
    "color": "31/a",
}

metric_info["open_file_descriptors"] = {
    "title": _("Open file descriptors"),
    "unit": "count",
    "color": "14/a",
}

metric_info["file_descriptors_open_attempts"] = {
    "title": _("File descriptor open attempts"),
    "unit": "count",
    "color": "21/a",
}

metric_info["file_descriptors_open_attempts_rate"] = {
    "title": _("File descriptor open attempts rate"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["max_file_descriptors"] = {
    "title": _("Max file descriptors"),
    "unit": "count",
    "color": "11/a",
}

metric_info["flush_time"] = {
    "title": _("Flush time"),
    "unit": "s",
    "color": "11/a",
}

metric_info["flushed"] = {
    "title": _("Flushes"),
    "unit": "count",
    "color": "21/a",
}

metric_info["avg_flush_time"] = {
    "title": _("Average flush time"),
    "unit": "s",
    "color": "31/a",
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

graph_info["shards_allocation"] = {
    "title": _("Shard allocation over time"),
    "metrics": [
        ("active_shards", "line"),
        ("active_primary_shards", "line"),
        ("relocating_shards", "line"),
        ("initializing_shards", "line"),
        ("unassigned_shards", "line"),
    ],
}

graph_info["active_shards"] = {
    "title": _("Active shards"),
    "metrics": [
        ("active_shards", "area"),
        ("active_primary_shards", "area"),
    ],
}
