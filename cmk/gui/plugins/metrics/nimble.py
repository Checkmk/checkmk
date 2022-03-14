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

for nimble_op_ty in ["read", "write"]:
    for nimble_key, nimble_title, nimble_color in [
        ("0.1", "0-0.1 ms", "32/a"),
        ("0.2", "0.1-0.2 ms", "31/a"),
        ("0.5", "0.2-0.5 ms", "26/a"),
        ("1", "0.5-1.0 ms", "25/a"),
        ("2", "1-2 ms", "24/a"),
        ("5", "2-5 ms", "23/a"),
        ("10", "5-10 ms", "22/a"),
        ("20", "10-20 ms", "21/a"),
        ("50", "20-50 ms", "16/a"),
        ("100", "50-100 ms", "15/a"),
        ("200", "100-200 ms", "14/a"),
        ("500", "200-500 ms", "13/a"),
        ("1000", "500+ ms", "12/a"),
    ]:
        metric_info["nimble_%s_latency_%s" % (nimble_op_ty, nimble_key.replace(".", ""))] = {
            "title": _("%s latency %s") % (nimble_op_ty.title(), nimble_title),
            "unit": "%",
            "color": nimble_color,
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

graph_info["read_latency"] = {
    "title": _("Percentage of Read I/O Operations per Latency Range"),
    "metrics": [
        ("nimble_read_latency_01", "line"),
        ("nimble_read_latency_02", "line"),
        ("nimble_read_latency_05", "line"),
        ("nimble_read_latency_1", "line"),
        ("nimble_read_latency_2", "line"),
        ("nimble_read_latency_5", "line"),
        ("nimble_read_latency_10", "line"),
        ("nimble_read_latency_20", "line"),
        ("nimble_read_latency_50", "line"),
        ("nimble_read_latency_100", "line"),
        ("nimble_read_latency_200", "line"),
        ("nimble_read_latency_500", "line"),
        ("nimble_read_latency_1000", "line"),
    ],
}

graph_info["write_latency"] = {
    "title": _("Percentage of Write I/O Operations per Latency Range"),
    "metrics": [
        ("nimble_write_latency_01", "line"),
        ("nimble_write_latency_02", "line"),
        ("nimble_write_latency_05", "line"),
        ("nimble_write_latency_1", "line"),
        ("nimble_write_latency_2", "line"),
        ("nimble_write_latency_5", "line"),
        ("nimble_write_latency_10", "line"),
        ("nimble_write_latency_20", "line"),
        ("nimble_write_latency_50", "line"),
        ("nimble_write_latency_100", "line"),
        ("nimble_write_latency_200", "line"),
        ("nimble_write_latency_500", "line"),
        ("nimble_write_latency_1000", "line"),
    ],
}
