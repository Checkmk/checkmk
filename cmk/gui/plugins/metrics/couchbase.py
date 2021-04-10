#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _

from cmk.gui.plugins.metrics import (
    metric_info,
    graph_info,
)

#.
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

metric_info["vbuckets"] = {
    "title": _("vBuckets"),
    "unit": "count",
    "color": "11/a",
}

metric_info["pending_vbuckets"] = {
    "title": _("Pending vBuckets"),
    "unit": "count",
    "color": "11/a",
}

metric_info["memused_couchbase_bucket"] = {
    "color": "#80ff40",
    "title": _("Memory used"),
    "unit": "bytes",
}

metric_info["mem_low_wat"] = {
    "title": _("Low watermark"),
    "unit": "bytes",
    "color": "#7060b0",
}

metric_info["mem_high_wat"] = {
    "title": _("High watermark"),
    "unit": "bytes",
    "color": "23/b",
}

metric_info["docs_fragmentation"] = {
    "title": _("Documents fragmentation"),
    "unit": "%",
    "color": "21/a",
}

metric_info["views_fragmentation"] = {
    "title": _("Views fragmentation"),
    "unit": "%",
    "color": "15/a",
}

#.
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

graph_info["couchbase_bucket_memory"] = {
    "title": _("Bucket memory"),
    "metrics": [
        ("memused_couchbase_bucket", "area"),
        ("mem_low_wat", "line"),
        ("mem_high_wat", "line"),
    ],
}

graph_info["couchbase_bucket_fragmentation"] = {
    "title": _("Fragmentation"),
    "metrics": [
        ("docs_fragmentation", "area"),
        ("views_fragmentation", "stack"),
    ],
}
