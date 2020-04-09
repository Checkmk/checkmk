#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Any  # pylint: disable=unused-import

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


def register_oracle_metrics():
    for what, descr, unit, color in [
        ("db_cpu", "DB CPU time", "1/s", "11/a"),
        ("db_time", "DB time", "1/s", "15/a"),
        ("buffer_hit_ratio", "buffer hit ratio", "%", "21/a"),
        ("physical_reads", "physical reads", "1/s", "43/b"),
        ("physical_writes", "physical writes", "1/s", "26/a"),
        ("db_block_gets", "block gets", "1/s", "13/a"),
        ("db_block_change", "block change", "1/s", "15/a"),
        ("consistent_gets", "consistent gets", "1/s", "23/a"),
        ("free_buffer_wait", "free buffer wait", "1/s", "25/a"),
        ("buffer_busy_wait", "buffer busy wait", "1/s", "41/a"),
        ("library_cache_hit_ratio", "library cache hit ratio", "%", "21/b"),
        ("pins_sum", "pins sum", "1/s", "41/a"),
        ("pin_hits_sum", "pin hits sum", "1/s", "46/a"),
    ]:
        metric_info["oracle_%s" % what] = {
            "title": _("ORACLE %s") % descr,
            "unit": unit,
            "color": color,
        }

    for what, descr, unit, color in [("oracle_sga_size", "SGA", "bytes", "11/a"),
                                     ("oracle_sga_buffer_cache", "Buffer Cache", "bytes", "15/a"),
                                     ("oracle_sga_shared_pool", "Shared Pool", "bytes", "21/a"),
                                     ("oracle_sga_redo_buffer", "Redo Buffer", "bytes", "43/b"),
                                     ("oracle_sga_java_pool", "Java Pool", "bytes", "26/a"),
                                     ("oracle_sga_large_pool", "Large Pool", "bytes", "14/a"),
                                     ("oracle_sga_streams_pool", "Streams Pool", "bytes", "16/a")]:
        metric_info["%s" % what] = {
            "title": _("ORACLE %s") % descr,
            "unit": unit,
            "color": color,
        }


register_oracle_metrics()

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

graph_info["oracle_physical_io"] = {
    "title": _("ORACLE physical IO"),
    "metrics": [
        ("oracle_physical_reads", "area"),
        ("oracle_physical_writes", "-area"),
    ]
}

graph_info["oracle_db_time_statistics"] = {
    "title": _("ORACLE DB time statistics"),
    "metrics": [
        ("oracle_db_cpu", "line"),
        ("oracle_db_time", "line"),
    ]
}

graph_info["oracle_buffer_pool_statistics"] = {
    "title": _("ORACLE buffer pool statistics"),
    "metrics": [
        ("oracle_db_block_gets", "line"),
        ("oracle_db_block_change", "line"),
        ("oracle_consistent_gets", "line"),
        ("oracle_free_buffer_wait", "line"),
        ("oracle_buffer_busy_wait", "line"),
    ],
}

graph_info["oracle_library_cache_statistics"] = {
    "title": _("ORACLE library cache statistics"),
    "metrics": [
        ("oracle_pins_sum", "line"),
        ("oracle_pin_hits_sum", "line"),
    ],
}

graph_info["oracle_sga_info"] = {
    "title": _("ORACLE SGA Information"),
    "metrics": [
        ("oracle_sga_size", "line"),
        ("oracle_sga_buffer_cache", "stack"),
        ("oracle_sga_shared_pool", "stack"),
        ("oracle_sga_redo_buffer", "stack"),
        ("oracle_sga_java_pool", "stack"),
        ("oracle_sga_large_pool", "stack"),
        ("oracle_sga_streams_pool", "stack"),
    ],
    "optional_metrics": [
        "oracle_sga_java_pool",
        "oracle_sga_large_pool",
        "oracle_sga_streams_pool",
    ],
}
