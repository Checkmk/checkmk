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

metric_info["backup_size"] = {
    "title": _("Backup size"),
    "unit": "bytes",
    "color": "12/a",
}

metric_info["job_duration"] = {
    "title": _("Job duration"),
    "unit": "s",
    "color": "33/a",
}

metric_info["backup_age"] = {
    "title": _("Time since last backup"),
    "unit": "s",
    "color": "34/a",
}

metric_info["logswitches_last_hour"] = {
    "title": _("Log switches in the last 60 minutes"),
    "unit": "count",
    "color": "#006040",
}

metric_info["direct_io"] = {
    "title": _("Direct I/O"),
    "unit": "bytes/s",
    "color": "21/a",
}

metric_info["buffered_io"] = {
    "title": _("Buffered I/O"),
    "unit": "bytes/s",
    "color": "23/a",
}

metric_info["write_cache_usage"] = {
    "title": _("Write cache usage"),
    "unit": "%",
    "color": "#030303",
}

metric_info["total_cache_usage"] = {
    "title": _("Total cache usage"),
    "unit": "%",
    "color": "#0ae86d",
}

metric_info["harddrive_power_cycles"] = {
    "title": _("Harddrive power cycles"),
    "unit": "count",
    "color": "11/a",
}

metric_info["harddrive_reallocated_sectors"] = {
    "title": _("Harddrive reallocated sectors"),
    "unit": "count",
    "color": "14/a",
}

metric_info["harddrive_reallocated_events"] = {
    "title": _("Harddrive reallocated events"),
    "unit": "count",
    "color": "21/a",
}

metric_info["harddrive_spin_retries"] = {
    "title": _("Harddrive spin retries"),
    "unit": "count",
    "color": "24/a",
}

metric_info["harddrive_pending_sectors"] = {
    "title": _("Harddrive pending sectors"),
    "unit": "count",
    "color": "31/a",
}

metric_info["harddrive_cmd_timeouts"] = {
    "title": _("Harddrive command timeouts"),
    "unit": "count",
    "color": "34/a",
}

metric_info["harddrive_end_to_end_errors"] = {
    "title": _("Harddrive end-to-end errors"),
    "unit": "count",
    "color": "41/a",
}

metric_info["harddrive_udma_crc_errors"] = {
    "title": _("Harddrive UDMA CRC errors"),
    "unit": "count",
    "color": "46/a",
}

metric_info["harddrive_uncorrectable_errors"] = {
    "title": _("Harddrive uncorrectable errors"),
    "unit": "count",
    "color": "13/a",
}

metric_info["storage_processor_util"] = {
    "title": _("Storage processor utilization"),
    "unit": "%",
    "color": "34/a",
}

metric_info["filehandler_perc"] = {
    "title": _("Used file handles"),
    "unit": "%",
    "color": "#4800ff",
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

metric_info["checkpoint_age"] = {
    "title": _("Time since last checkpoint"),
    "unit": "s",
    "color": "#006040",
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

graph_info["backup_time"] = {
    "title": _("Backup time"),
    "metrics": [("checkpoint_age", "area"), ("backup_age", "stack")],
}

graph_info["total_cache_usage"] = {
    "title": _("Total cache usage"),
    "metrics": [("total_cache_usage", "area")],
    "range": (0, 100),
}

graph_info["write_cache_usage"] = {
    "title": _("Write cache usage"),
    "metrics": [("write_cache_usage", "area")],
    "range": (0, 100),
}

# diskstat checks

graph_info["direct_and_buffered_io_operations"] = {
    "title": _("Direct and buffered I/O operations"),
    "metrics": [
        ("direct_io", "stack"),
        ("buffered_io", "stack"),
    ],
}

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

graph_info["harddrive_health_statistic"] = {
    "title": _("Harddrive health statistic"),
    "metrics": [
        ("harddrive_power_cycles", "stack"),
        ("harddrive_reallocated_sectors", "stack"),
        ("harddrive_reallocated_events", "stack"),
        ("harddrive_spin_retries", "stack"),
        ("harddrive_pending_sectors", "stack"),
        ("harddrive_cmd_timeouts", "stack"),
        ("harddrive_end_to_end_errors", "stack"),
        ("harddrive_uncorrectable_errors", "stack"),
        ("harddrive_udma_crc_errors", "stack"),
    ],
}
