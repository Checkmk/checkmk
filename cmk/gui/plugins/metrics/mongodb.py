#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.metrics.utils import metric_info

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

metric_info["mongodb_chunk_count"] = {
    "title": _("Number of Chunks"),
    "help": _("Number of jumbo chunks per collection"),
    "color": "#924d85",
    "unit": "count",
}

metric_info["mongodb_jumbo_chunk_count"] = {
    "title": _("Jumbo Chunks"),
    "help": _("Number of jumbo chunks per collection"),
    "color": "#91457d",
    "unit": "count",
}


def register_assert_metrics():
    for what, color in [
        ("msg", "12"),
        ("rollovers", "13"),
        ("regular", "14"),
        ("warning", "15"),
        ("user", "16"),
    ]:
        metric_info["assert_%s" % what] = {
            "title": _("%s Asserts") % what.title(),
            "unit": "count",
            "color": "%s/a" % color,
        }


register_assert_metrics()

metric_info["mongodb_collection_size"] = {
    "title": _("Collection Size"),
    "help": _("Uncompressed size in memory"),
    "color": "#3b4080",
    "unit": "bytes",
}

metric_info["mongodb_collection_storage_size"] = {
    "title": _("Storage Size"),
    "help": _("Allocated for document storage"),
    "color": "#4d5092",
    "unit": "bytes",
}

metric_info["mongodb_collection_total_index_size"] = {
    "title": _("Total Index Size"),
    "help": _("The total size of all indexes for the collection"),
    "color": "#535687",
    "unit": "bytes",
}

metric_info["mongodb_replication_info_log_size"] = {
    "title": _("Total size of the oplog"),
    "help": _(
        "Total amount of space allocated to the oplog rather than the current size of operations stored in the oplog"
    ),
    "color": "#3b4080",
    "unit": "bytes",
}

metric_info["mongodb_replication_info_used"] = {
    "title": _("Total amount of space used by the oplog"),
    "help": _(
        "Total amount of space currently used by operations stored in the oplog rather than the total amount of space allocated"
    ),
    "color": "#4d5092",
    "unit": "bytes",
}

metric_info["mongodb_replication_info_time_diff"] = {
    "title": _("Difference between the first and last operation in the oplog"),
    "help": _("Difference between the first and last operation in the oplog in seconds"),
    "color": "#535687",
    "unit": "s",
}

metric_info["mongodb_document_count"] = {
    "title": _("Number of Documents"),
    "help": _("Number of documents per collection"),
    "color": "#60ad54",
    "unit": "count",
}
