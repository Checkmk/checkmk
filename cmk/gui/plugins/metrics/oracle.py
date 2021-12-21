#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.oracle_constants import (
    oracle_io_sizes,
    oracle_io_types,
    oracle_iofiles,
    oracle_sga_fields,
    oracle_waitclasses,
)

from cmk.gui.i18n import _
from cmk.gui.plugins.metrics.utils import graph_info, indexed_color, metric_info

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


def register_oracle_metrics():
    # waitclass totals
    metric_info["oracle_wait_class_total"] = {
        "title": _("ORACLE Total waited"),
        "unit": "1/s",
        "color": "#100",
    }
    metric_info["oracle_wait_class_total_fg"] = {
        "title": _("ORACLE Total waited (FG)"),
        "unit": "1/s",
        "color": "#100",
    }

    # waitclasses
    for index, waitclass in enumerate(oracle_waitclasses):
        metric_info[waitclass.metric] = {
            "title": _("ORACLE %s wait class") % waitclass.name,
            "unit": "1/s",
            "color": indexed_color(index + 1, len(oracle_waitclasses)),
        }
        metric_info[waitclass.metric_fg] = {
            "title": _("ORACLE %s wait class (FG)") % waitclass.name,
            "unit": "1/s",
            "color": indexed_color(index + 1, len(oracle_waitclasses)),
        }

    # iofiles
    color_index = 0
    for iofile_name, iofile_id in oracle_iofiles:
        for size_code, size_text in oracle_io_sizes:
            color_index += 1
            for io_code, io_text, unit in oracle_io_types:
                metric_info["oracle_ios_f_%s_%s_%s" % (iofile_id, size_code, io_code)] = {
                    "title": _("ORACLE %s %s %s") % (iofile_name, size_text, io_text),
                    "unit": unit,
                    "color": indexed_color(color_index, len(oracle_iofiles) * len(oracle_io_sizes)),
                }

    # iofiles totals
    metric_info["oracle_ios_f_total_s_rb"] = {
        "title": _("ORACLE Total Small Read Bytes"),
        "unit": "bytes/s",
        "color": "#50d090",
    }
    metric_info["oracle_ios_f_total_s_wb"] = {
        "title": _("ORACLE Total Small Write Bytes"),
        "unit": "bytes/s",
        "color": "#5090d0",
    }
    metric_info["oracle_ios_f_total_l_rb"] = {
        "title": _("ORACLE Total Large Read Bytes"),
        "unit": "bytes/s",
        "color": "#30b070",
    }
    metric_info["oracle_ios_f_total_l_wb"] = {
        "title": _("ORACLE Total Large Write Bytes"),
        "unit": "bytes/s",
        "color": "#3070b0",
    }
    metric_info["oracle_ios_f_total_s_r"] = {
        "title": _("ORACLE Total Small Reads"),
        "unit": "1/s",
        "color": "#50d090",
    }
    metric_info["oracle_ios_f_total_s_w"] = {
        "title": _("ORACLE Total Small Writes"),
        "unit": "1/s",
        "color": "#5090d0",
    }
    metric_info["oracle_ios_f_total_l_r"] = {
        "title": _("ORACLE Total Large Reads"),
        "unit": "1/s",
        "color": "#30b070",
    }
    metric_info["oracle_ios_f_total_l_w"] = {
        "title": _("ORACLE Total Large Writes"),
        "unit": "1/s",
        "color": "#3070b0",
    }

    # SGAs
    for index, sga in enumerate(oracle_sga_fields):
        metric_info[sga.metric] = {
            "title": _("ORACLE %s") % sga.name,
            "unit": "bytes",
            "color": indexed_color(index + 1, len(oracle_sga_fields)),
        }

    # PGAs
    metric_info["oracle_pga_total_pga_allocated"] = {
        "title": ("ORACLE total PGA allocated"),
        "unit": "bytes",
        "color": "#e0e0e0",
    }
    metric_info["oracle_pga_total_pga_inuse"] = {
        "title": ("ORACLE total PGA inuse"),
        "unit": "bytes",
        "color": "#71ad9f",
    }
    metric_info["oracle_pga_total_freeable_pga_memory"] = {
        "title": ("ORACLE total freeable PGA memory"),
        "unit": "bytes",
        "color": "#7192ad",
    }

    # other metrics
    for what, descr, unit, color in [
        ("db_cpu", "DB CPU time", "1/s", "#60f020"),
        ("db_time", "DB time", "1/s", "#004080"),
        ("db_wait_time", "DB Non-Idle Wait", "1/s", "00b0c0"),
        ("buffer_hit_ratio", "buffer hit ratio", "%", "21/a"),
        ("physical_reads", "physical reads", "1/s", "43/b"),
        ("physical_writes", "physical writes", "1/s", "26/a"),
        ("db_block_gets", "block gets", "1/s", "13/a"),
        ("db_block_change", "block change", "1/s", "15/a"),
        ("consistent_gets", "consistent gets", "1/s", "21/a"),
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


register_oracle_metrics()

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


def register_oracle_graphs():
    graph_info["oracle_physical_io"] = {
        "title": _("ORACLE physical IO"),
        "metrics": [
            ("oracle_physical_reads", "area"),
            ("oracle_physical_writes", "-area"),
        ],
    }
    graph_info["oracle_hit_ratio"] = {
        "title": _("ORACLE hit ratio"),
        "metrics": [
            ("oracle_buffer_hit_ratio", "area"),
            ("oracle_library_cache_hit_ratio", "-area"),
        ],
    }
    graph_info["oracle_db_time_statistics"] = {
        "title": _("ORACLE DB time statistics"),
        "metrics": [
            ("oracle_db_cpu", "stack"),
            ("oracle_db_wait_time", "stack"),
            ("oracle_db_time", "line"),
        ],
        "optional_metrics": ["oracle_db_wait_time"],
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
    graph_info["oracle_sga_pga_total"] = {
        "title": _("ORACLE Memory"),
        "metrics": [
            ("oracle_sga_size#80ff40", "stack"),
            ("oracle_pga_total_pga_allocated#408f20", "stack"),
            ("oracle_sga_size,oracle_pga_total_pga_allocated,+", "line", _("ORACLE total Memory")),
        ],
    }
    graph_info["oracle_sga_info"] = {
        "title": _("ORACLE SGA memory statistics"),
        "metrics": [
            ("oracle_sga_size", "line"),
            ("oracle_sga_buffer_cache", "stack"),
            ("oracle_sga_shared_pool", "stack"),
            ("oracle_sga_shared_io_pool", "stack"),
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
    iostat_bytes_metrics = []
    iostat_ios_metrics = []
    for iofile in oracle_iofiles:
        for size in ["s", "l"]:
            iostat_bytes_metrics.append(("oracle_ios_f_%s_%s_rb" % (iofile.id, size), "line"))
            iostat_ios_metrics.append(("oracle_ios_f_%s_%s_r" % (iofile.id, size), "line"))
    for iofile in oracle_iofiles:
        for size in ["s", "l"]:
            iostat_bytes_metrics.append(("oracle_ios_f_%s_%s_wb" % (iofile.id, size), "-line"))
            iostat_ios_metrics.append(("oracle_ios_f_%s_%s_w" % (iofile.id, size), "-line"))
    graph_info["oracle_iostat_bytes"] = {
        "title": _("ORACLE IOSTAT Bytes"),
        "metrics": iostat_bytes_metrics,
        "omit_zero_metrics": True,
    }
    graph_info["oracle_iostat_total_bytes"] = {
        "title": _("ORACLE IOSTAT Total Bytes"),
        "metrics": [
            ("oracle_ios_f_total_s_rb", "line"),
            ("oracle_ios_f_total_s_wb", "-line"),
            ("oracle_ios_f_total_l_rb", "line"),
            ("oracle_ios_f_total_l_wb", "-line"),
        ],
    }
    graph_info["oracle_iostat_ios"] = {
        "title": _("ORACLE IOSTAT IOs"),
        "metrics": iostat_ios_metrics,
        "omit_zero_metrics": True,
    }
    graph_info["oracle_iostat_total_ios"] = {
        "title": _("ORACLE IOSTAT Total IOs"),
        "metrics": [
            ("oracle_ios_f_total_s_r", "line"),
            ("oracle_ios_f_total_s_w", "-line"),
            ("oracle_ios_f_total_l_r", "line"),
            ("oracle_ios_f_total_l_w", "-line"),
        ],
    }
    graph_info["oracle_wait_class"] = {
        "title": _("ORACLE Wait Class (FG lines are downside)"),
        "metrics": [("oracle_wait_class_total", "line")]
        + [(waitclass.metric, "line") for waitclass in oracle_waitclasses]
        +
        #######################################################
        [("oracle_wait_class_total_fg", "-line")]
        + [(waitclass.metric_fg, "-line") for waitclass in oracle_waitclasses],
        "omit_zero_metrics": True,
        "optional_metrics": [waitclass.metric for waitclass in oracle_waitclasses]
        + [waitclass.metric_fg for waitclass in oracle_waitclasses],
    }
    graph_info["oracle_pga_memory_info"] = {
        "title": _("ORACLE PGA memory statistics"),
        "metrics": [
            ("oracle_pga_total_pga_allocated", "area"),
            ("oracle_pga_total_pga_inuse", "area"),
            ("oracle_pga_total_freeable_pga_memory", "area"),
        ],
        "optional_metrics": ["oracle_pga_total_freeable_pga_memory"],
    }


register_oracle_graphs()
