#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Any  # pylint: disable=unused-import
import cmk.utils.render

from cmk.gui.i18n import _

from cmk.gui.plugins.metrics import (
    unit_info,
    metric_info,
    check_metrics,
    graph_info,
    perfometer_info,
    KB,
    MB,
    GB,
    TB,
    m,
    parse_color_into_hexrgb,
    MAX_CORES,
    indexed_color,
)
from cmk.utils.aws_constants import AWSEC2InstTypes, AWSEC2InstFamilies

# TODO Graphingsystem:
# - Default-Template: Wenn im Graph kein "range" angegeben ist, aber
# in der Unit eine "range"-Angabe ist, dann soll diese genommen werden.
# Und dann sämtliche Schablonen, die nur wegen Range
# 0..100 da sind, wieder durch generic ersetzen.

# Metric definitions for Check_MK's checks

#   .--Units---------------------------------------------------------------.
#   |                        _   _       _ _                               |
#   |                       | | | |_ __ (_) |_ ___                         |
#   |                       | | | | '_ \| | __/ __|                        |
#   |                       | |_| | | | | | |_\__ \                        |
#   |                        \___/|_| |_|_|\__|___/                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Definition of units of measurement.                                 |
#   '----------------------------------------------------------------------'
# Optional attributes of units:
#
#   stepping: FIXME: Describe this
#
#   graph_unit: Compute a common unit for the whole graph. This is an optional
#               feature to solve the problem that some unit names are too long
#               to be shown on the left of the screen together with the values.
#               For fixing this the "graph unit" is available which is displayed
#               on the top left of the graph and is used for the whole graph. So
#               once a "graph unit" is computed, it does not need to be shown
#               beside each label.
#               This has to be set to a function which recevies a list of values,
#               then computes the optimal unit for the given values and then
#               returns a two element tuple. The first element is the "graph unit"
#               and the second is a list containing all of the values rendered with
#               the graph unit.

# TODO: Move fundamental units like "" to main file.

unit_info[""] = {
    "title": "",
    "description": _("Floating point number"),
    "symbol": "",
    "render": lambda v: cmk.utils.render.scientific(v, 2),
}

unit_info["count"] = {
    "title": _("Count"),
    "symbol": "",
    "render": lambda v: cmk.utils.render.fmt_number_with_precision(v, drop_zeroes=True),
    "stepping": "integer",  # for vertical graph labels
}

# value ranges from 0.0 ... 100.0
unit_info["%"] = {
    "title": _("%"),
    "description": _("Percentage (0...100)"),
    "symbol": _("%"),
    "render": lambda v: cmk.utils.render.percent(v, scientific_notation=True),
}

unit_info["s"] = {
    "title": _("sec"),
    "description": _("Timespan or Duration in seconds"),
    "symbol": _("s"),
    "render": cmk.utils.render.approx_age,
    "stepping": "time",  # for vertical graph labels
}

unit_info["1/s"] = {
    "title": _("per second"),
    "description": _("Frequency (displayed in events/s)"),
    "symbol": _("/s"),
    "render": lambda v: "%s%s" % (cmk.utils.render.drop_dotzero(v), _("/s")),
}

unit_info["hz"] = {
    "title": _("Hz"),
    "symbol": _("Hz"),
    "description": _("Frequency (displayed in Hz)"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("Hz")),
}

unit_info["bytes"] = {
    "title": _("Bytes"),
    "symbol": _("B"),
    "render": cmk.utils.render.fmt_bytes,
    "stepping": "binary",  # for vertical graph labels
}

unit_info["bytes/s"] = {
    "title": _("Bytes per second"),
    "symbol": _("B/s"),
    "render": lambda v: cmk.utils.render.fmt_bytes(v) + _("/s"),
    "stepping": "binary",  # for vertical graph labels
}


def physical_precision_list(values, precision, unit_symbol):
    if not values:
        reference = 0
    else:
        reference = min([abs(v) for v in values])

    scale_symbol, places_after_comma, scale_factor = cmk.utils.render.calculate_physical_precision(
        reference, precision)

    scaled_values = []
    for value in values:
        scaled_value = float(value) / scale_factor
        scaled_values.append(("%%.%df" % places_after_comma) % scaled_value)

    return "%s%s" % (scale_symbol, unit_symbol), scaled_values


unit_info["bits/s"] = {
    "title": _("Bits per second"),
    "symbol": _("bits/s"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("bit/s")),
    "graph_unit": lambda v: physical_precision_list(v, 3, _("bit/s")),
}


def bytes_human_readable_list(values, *args, **kwargs):
    if not values:
        reference = 0
    else:
        reference = min([abs(v) for v in values])

    scale_factor, scale_prefix = cmk.utils.render.scale_factor_prefix(reference, 1024.0)
    precision = kwargs.get("precision", 2)

    scaled_values = ["%.*f" % (precision, float(value) / scale_factor) for value in values]

    unit_txt = kwargs.get("unit", "B")

    return scale_prefix + unit_txt, scaled_values


# Output in bytes/days, value is in bytes/s
unit_info["bytes/d"] = {
    "title": _("Bytes per day"),
    "symbol": _("B/d"),
    "render": lambda v: cmk.utils.render.fmt_bytes(v * 86400.0) + "/d",
    "graph_unit": lambda values: bytes_human_readable_list([v * 86400.0 for v in values],
                                                           unit=_("B/d")),
    "stepping": "binary",  # for vertical graph labels
}

unit_info["c"] = {
    "title": _("Degree Celsius"),
    "symbol": u"°C",
    "render": lambda v: "%s %s" % (cmk.utils.render.drop_dotzero(v), u"°C"),
}

unit_info["a"] = {
    "title": _("Electrical Current (Amperage)"),
    "symbol": _("A"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("A")),
}

unit_info["v"] = {
    "title": _("Electrical Tension (Voltage)"),
    "symbol": _("V"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("V")),
}

unit_info["w"] = {
    "title": _("Electrical Power"),
    "symbol": _("W"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("W")),
}

unit_info["va"] = {
    "title": _("Electrical Apparent Power"),
    "symbol": _("VA"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("VA")),
}

unit_info["wh"] = {
    "title": _("Electrical Energy"),
    "symbol": _("Wh"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("Wh")),
}

unit_info["dbm"] = {
    "title": _("Decibel-milliwatts"),
    "symbol": _("dBm"),
    "render": lambda v: "%s %s" % (cmk.utils.render.drop_dotzero(v), _("dBm")),
}

unit_info["dbmv"] = {
    "title": _("Decibel-millivolt"),
    "symbol": _("dBmV"),
    "render": lambda v: "%s %s" % (cmk.utils.render.drop_dotzero(v), _("dBmV")),
}

unit_info["db"] = {
    "title": _("Decibel"),
    "symbol": _("dB"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("dB")),
}

unit_info["ppm"] = {
    "title": _("ppm"),
    "symbol": _("ppm"),
    "description": _("Parts per Million"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("ppm")),
}

# 'Percent obscuration per meter'-Obscuration for any atmospheric phenomenon, e.g. smoke, dust, snow
unit_info["%/m"] = {
    "title": _("Percent Per Meter"),
    "symbol": _("%/m"),
    "render": lambda v: cmk.utils.render.percent(v, scientific_notation=True) + _("/m"),
}

unit_info["bar"] = {
    "title": _("Bar"),
    "symbol": _("bar"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 4, _("bar")),
}

unit_info["pa"] = {
    "title": _("Pascal"),
    "symbol": _("Pa"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("Pa")),
}

unit_info["l/s"] = {
    "title": _("Liters per second"),
    "symbol": _("l/s"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 3, _("l/s")),
}

unit_info["rpm"] = {
    "title": _("Rotations per minute"),
    "symbol": _("rpm"),
    "render": lambda v: cmk.utils.render.physical_precision(v, 4, _("rpm")),
}

unit_info['bytes/op'] = {
    'title': _('Read size per operation'),
    'symbol': 'bytes/op',
    'color': '#4080c0',
    "render": cmk.utils.render.fmt_bytes,
}

unit_info['EUR'] = {
    "title": _("Euro"),
    "symbol": u"€",
    "render": lambda v: u"%s €" % v,
}

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

MAX_NUMBER_HOPS = 45  # the amount of hop metrics, graphs and perfometers to create


def register_hop_metrics():
    for idx in range(0, MAX_NUMBER_HOPS):
        if idx:
            prefix_perf = "hop_%d_" % idx
            prefix_text = "Hop %d " % idx
        else:
            prefix_perf = ""
            prefix_text = ""

        metric_info["%srta" % prefix_perf] = {
            "title": _("%sRound trip average") % prefix_text,
            "unit": "s",
            "color": "33/a"
        }

        metric_info["%srtmin" % prefix_perf] = {
            "title": _("%sRound trip minimum") % prefix_text,
            "unit": "s",
            "color": "42/a",
        }

        metric_info["%srtmax" % prefix_perf] = {
            "title": _("%sRound trip maximum") % prefix_text,
            "unit": "s",
            "color": "42/b",
        }

        metric_info["%srtstddev" % prefix_perf] = {
            "title": _("%sRound trip standard devation") % prefix_text,
            "unit": "s",
            "color": "16/a",
        }

        metric_info["%spl" % prefix_perf] = {
            "title": _("%sPacket loss") % prefix_text,
            "unit": "%",
            "color": "#ffc030",
        }

        metric_info["%sresponse_time" % prefix_perf] = {
            "title": _("%sResponse time") % prefix_text,
            "unit": "s",
            "color": "23/a"
        }


register_hop_metrics()

metric_info["accepted"] = {
    "title": _("Accepted connections"),
    "unit": "count",
    "color": "11/a",
}

metric_info["accepted_per_sec"] = {
    "title": _("Accepted connections per second"),
    "unit": "1/s",
    "color": "16/a",
}

metric_info["handled"] = {
    "title": _("Handled connections"),
    "unit": "count",
    "color": "21/a",
}

metric_info["handled_per_sec"] = {
    "title": _("Handled connections per second"),
    "unit": "1/s",
    "color": "26/a",
}

metric_info["requests"] = {
    "title": _("Requests per second"),
    "unit": "count",
    "color": "31/a",
}

metric_info["requests_per_conn"] = {
    "title": _("Requests per connection"),
    "unit": "count",
    "color": "33/a",
}

metric_info["requests_per_sec"] = {
    "title": _("Requests per second"),
    "unit": "1/s",
    "color": "36/a",
}

metric_info["active"] = {
    "title": _("Active connections"),
    "unit": "count",
    "color": "11/a",
}

metric_info["reading"] = {
    "title": _("Reading connections"),
    "unit": "count",
    "color": "16/a",
}

metric_info["waiting"] = {
    "title": _("Waiting connections"),
    "unit": "count",
    "color": "21/a",
}

metric_info["writing"] = {
    "title": _("Writing connections"),
    "unit": "count",
    "color": "21/a",
}

metric_info["apply_finish_time"] = {
    "title": _("Apply Finish Time"),
    "unit": "s",
    "color": "11/a",
}

metric_info["transport_lag"] = {
    "title": _("Transport Lag"),
    "unit": "s",
    "color": "16/a",
}

metric_info["apply_lag"] = {
    "title": _("Apply Lag"),
    "unit": "s",
    "color": "21/a",
}

metric_info["rtt"] = {
    "title": _("Round trip time"),
    "unit": "s",
    "color": "33/a",
}

metric_info["hops"] = {
    "title": _("Number of hops"),
    "unit": "count",
    "color": "51/a",
}

metric_info["uptime"] = {
    "title": _("Uptime"),
    "unit": "s",
    "color": "#80f000",
}

metric_info["time_difference"] = {
    "title": _("Time difference"),
    "unit": "s",
    "color": "#80f000",
}

metric_info["age"] = {
    "title": _("Age"),
    "unit": "s",
    "color": "#80f000",
}

metric_info["age_oldest"] = {
    "title": _("Oldest age"),
    "unit": "s",
    "color": "35/a",
}

metric_info["last_updated"] = {
    "title": _("Last Updated"),
    "unit": "s",
    "color": "#80f000",
}

metric_info["deferred_age"] = {
    "title": _("Deferred Files Age"),
    "unit": "s",
    "color": "#80f000",
}

metric_info["runtime"] = {
    "title": _("Process Runtime"),
    "unit": "s",
    "color": "#80f000",
}

metric_info["lifetime_remaining"] = {
    "title": _("Lifetime remaining"),
    "unit": "s",
    "color": "#80f000",
}

metric_info["streams"] = {
    "title": _("Streams"),
    "unit": "%",
    "color": "35/a",
}

metric_info["cache_misses_rate"] = {
    "title": _("Cache misses per second"),
    "unit": "1/s",
    "color": "#ba60ba",
}

metric_info["cache_hit_ratio"] = {
    "title": _("Cache hit ratio"),
    "unit": "%",
    "color": "#60c0c0",
}

metric_info["zfs_l2_hit_ratio"] = {
    "title": _("L2 cache hit ratio"),
    "unit": "%",
    "color": "46/a",
}

metric_info["prefetch_data_hit_ratio"] = {
    "title": _("Prefetch data hit ratio"),
    "unit": "%",
    "color": "41/b",
}

metric_info["prefetch_metadata_hit_ratio"] = {
    "title": _("Prefetch metadata hit ratio"),
    "unit": "%",
    "color": "43/a",
}

metric_info["zfs_metadata_used"] = {
    "title": _("Used meta data"),
    "unit": "bytes",
    "color": "31/a",
}

metric_info["zfs_metadata_max"] = {
    "title": _("Maxmimum of meta data"),
    "unit": "bytes",
    "color": "33/a",
}

metric_info["zfs_metadata_limit"] = {
    "title": _("Limit of meta data"),
    "unit": "bytes",
    "color": "36/a",
}

metric_info["zfs_l2_size"] = {
    "title": _("L2 cache size"),
    "unit": "bytes",
    "color": "31/a",
}

metric_info["file_size"] = {
    "title": _("File size"),
    "unit": "bytes",
    "color": "16/a",
}

metric_info["total_file_size"] = {
    "title": _("Total file size"),
    "unit": "bytes",
    "color": "16/a",
}
metric_info["file_size_smallest"] = {
    "title": _("Smallest file"),
    "unit": "bytes",
    "color": "21/a",
}

metric_info["file_size_largest"] = {
    "title": _("Largest file"),
    "unit": "bytes",
    "color": "25/a",
}

metric_info["file_count"] = {
    "title": _("Amount of files"),
    "unit": "count",
    "color": "23/a",
}

metric_info["new_files"] = {
    "title": _("New files in Spool"),
    "unit": "count",
    "color": "23/a",
}

metric_info["deferred_files"] = {
    "title": _("Deferred files in Spool"),
    "unit": "count",
    "color": "16/a",
}

metric_info["corrupted_files"] = {
    "title": _("Corrupted files in Spool"),
    "unit": "count",
    "color": "34/a",
}

# cloud storage

metric_info["used_space"] = {
    "title": _("Used storage space"),
    "unit": "bytes",
    "color": "34/a",
}

metric_info["ingress"] = {
    "title": _("Data ingress"),
    "unit": "bytes",
    "color": "15/a",
}

metric_info["egress"] = {
    "title": _("Data engress"),
    "unit": "bytes",
    "color": "43/a",
}

metric_info["transactions"] = {
    "title": _("Transaction count"),
    "unit": "count",
    "color": "36/a",
}

metric_info["server_latency"] = {
    "title": _("Server latency"),
    "unit": "s",
    "color": "21/a",
}

metric_info["e2e_latency"] = {
    "title": _("End-to-end latency"),
    "unit": "s",
    "color": "21/b",
}

metric_info["availability"] = {
    "title": _("Availability"),
    "unit": "%",
    "color": "31",
}

# database, tablespace

metric_info["data_files"] = {
    "title": _("Data files size"),
    "unit": "bytes",
    "color": "34/a",
}

metric_info["log_files_used"] = {
    "title": _("Used size of log files"),
    "unit": "bytes",
    "color": "25/a",
}

metric_info["log_files_total"] = {
    "title": _("Total size of log files"),
    "unit": "bytes",
    "color": "16/a",
}

metric_info["database_size"] = {
    "title": _("Database size"),
    "unit": "bytes",
    "color": "16/a",
}

metric_info["data_size"] = {
    "title": _("Data size"),
    "unit": "bytes",
    "color": "25/a",
}

metric_info["size_on_disk"] = {
    "title": _("Size on disk"),
    "unit": "bytes",
    "color": "25/b",
}

metric_info["unallocated_size"] = {
    "title": _("Unallocated space"),
    "help": _("Space in the database that has not been reserved for database objects"),
    "unit": "bytes",
    "color": "34/a",
}

metric_info["reserved_size"] = {
    "title": _("Reserved space"),
    "help": _("Total amount of space allocated by objects in the database"),
    "unit": "bytes",
    "color": "41/a",
}

metric_info["indexes_size"] = {
    "title": _("Index space"),
    "unit": "bytes",
    "color": "31/a",
}

metric_info["unused_size"] = {
    "title": _("Unused space"),
    "help": _("Total amount of space reserved for objects in the database, but not yed used"),
    "unit": "bytes",
    "color": "46/a",
}

metric_info["allocated_size"] = {
    "title": _("Allocated space"),
    "unit": "bytes",
    "color": "42/a",
}

metric_info["tablespace_size"] = {
    "title": _("Tablespace size"),
    "unit": "bytes",
    "color": "#092507",
}

metric_info["tablespace_used"] = {
    "title": _("Tablespace used"),
    "unit": "bytes",
    "color": "#e59d12",
}

metric_info["tablespace_max_size"] = {
    "title": _("Tablespace maximum size"),
    "unit": "bytes",
    "color": "#172121",
}

metric_info["tablespace_wasted"] = {
    "title": _("Tablespace wasted"),
    "unit": "bytes",
    "color": "#a02020",
}

metric_info["indexspace_wasted"] = {
    "title": _("Indexspace wasted"),
    "unit": "bytes",
    "color": "#20a080",
}

metric_info["database_reclaimable"] = {
    "title": _("Database reclaimable size"),
    "unit": "bytes",
    "color": "45/a",
}

metric_info["mem_total"] = {
    "title": _("RAM installed"),
    "color": "#f0f0f0",
    "unit": "bytes",
}

metric_info["memory_avg"] = {
    "title": _("Memory Average"),
    "color": "#80ff40",
    "unit": "bytes",
}

metric_info["pagefile_avg"] = {
    "title": _("Commit Charge Average"),
    "color": "#408f20",
    "unit": "bytes",
}

metric_info["mem_free"] = {
    "title": _("Free RAM"),
    "color": "#ffffff",
    "unit": "bytes",
}

metric_info["mem_used"] = {
    "color": "#80ff40",
    "title": _("RAM used"),
    "unit": "bytes",
}

metric_info["mem_available"] = {
    "color": "21/a",
    "title": _("Estimated RAM for new processes"),
    "unit": "bytes",
}

metric_info["pagefile_used"] = {
    "color": "#408f20",
    "title": _("Commit Charge"),
    "unit": "bytes",
}

metric_info["mem_used_percent"] = {
    "color": "#80ff40",
    "title": _("RAM used %"),
    "unit": "%",
}

metric_info["cpu_mem_used_percent"] = {
    "color": "#80ff40",
    "title": _("CPU Memory used"),
    "unit": "%",
}

metric_info["mem_perm_used"] = {
    "color": "#80ff40",
    "title": _("Permanent Generation Memory"),
    "unit": "bytes",
}

metric_info["mem_growth"] = {
    "title": _("Memory usage growth"),
    "unit": "bytes/d",
    "color": "#29cfaa",
}

metric_info["mem_trend"] = {
    "title": _("Trend of memory usage growth"),
    "unit": "bytes/d",
    "color": "#808080",
}

metric_info["trend_hoursleft"] = {
    "title": _("Time left until full"),
    "unit": "s",
    "color": "#94b65a",
}

metric_info["power_usage_percentage"] = {
    "title": _("Power Usage"),
    "color": "13/a",
    "unit": "%",
}

metric_info["power_usage"] = {
    "title": _("Power Usage"),
    "color": "13/b",
    "unit": "w",
}

metric_info["swap_total"] = {
    "title": _("Swap installed"),
    "color": "#e0e0e0",
    "unit": "bytes",
}

metric_info["swap_free"] = {
    "title": _("Free swap space"),
    "unit": "bytes",
    "color": "#eeeeee",
}

metric_info["swap_used"] = {
    "title": _("Swap used"),
    "color": "#408f20",
    "unit": "bytes",
}

metric_info["swap_used_percent"] = {
    "color": "#408f20",
    "title": _("Swap used"),
    "unit": "%",
}

metric_info["swap_cached"] = {
    "title": _("Swap cached"),
    "color": "#5bebc9",
    "unit": "bytes",
}

metric_info["caches"] = {
    "title": _("Memory used by caches"),
    "unit": "bytes",
    "color": "51/a",
}

metric_info["mem_pages_rate"] = {
    "title": _("Memory Pages"),
    "unit": "1/s",
    "color": "34/a",
}

metric_info["mem_lnx_total_used"] = {
    "title": _("Total used memory"),
    "color": "#70f038",
    "unit": "bytes",
}

metric_info["mem_lnx_cached"] = {
    "title": _("Cached memory"),
    "color": "#91cceb",
    "unit": "bytes",
}

metric_info["mem_lnx_buffers"] = {
    "title": _("Buffered memory"),
    "color": "#5bb9eb",
    "unit": "bytes",
}

metric_info["mem_lnx_slab"] = {
    "title": _("Slab (Various smaller caches)"),
    "color": "#af91eb",
    "unit": "bytes",
}

metric_info["mem_lnx_sreclaimable"] = {
    "title": _("Reclaimable memory"),
    "color": "23/a",
    "unit": "bytes",
}

metric_info["mem_lnx_sunreclaim"] = {
    "title": _("Unreclaimable memory"),
    "color": "24/a",
    "unit": "bytes",
}

metric_info["mem_lnx_pending"] = {
    "title": _("Pending memory"),
    "color": "25/a",
    "unit": "bytes",
}

metric_info["mem_lnx_unevictable"] = {
    "title": _("Unevictable memory"),
    "color": "26/a",
    "unit": "bytes",
}

metric_info["mem_lnx_anon_pages"] = {
    "title": _("Anonymous pages"),
    "color": "#cc4040",
    "unit": "bytes",
}

metric_info["mem_lnx_active_anon"] = {
    "title": _("Active (anonymous)"),
    "color": "#ff4040",
    "unit": "bytes",
}

metric_info["mem_lnx_active_file"] = {
    "title": _("Active (files)"),
    "color": "#ff8080",
    "unit": "bytes",
}

metric_info["mem_lnx_inactive_anon"] = {
    "title": _("Inactive (anonymous)"),
    "color": "#377cab",
    "unit": "bytes",
}

metric_info["mem_lnx_inactive_file"] = {
    "title": _("Inactive (files)"),
    "color": "#4eb0f2",
    "unit": "bytes",
}

metric_info["mem_lnx_active"] = {
    "title": _("Active"),
    "color": "#ff4040",
    "unit": "bytes",
}

metric_info["mem_lnx_inactive"] = {
    "title": _("Inactive"),
    "color": "#4040ff",
    "unit": "bytes",
}

metric_info["mem_lnx_dirty"] = {
    "title": _("Dirty disk blocks"),
    "color": "#f2904e",
    "unit": "bytes",
}

metric_info["mem_lnx_writeback"] = {
    "title": _("Currently being written"),
    "color": "#f2df40",
    "unit": "bytes",
}

metric_info["mem_lnx_nfs_unstable"] = {
    "title": _("Modified NFS data"),
    "color": "#c6f24e",
    "unit": "bytes",
}

metric_info["mem_lnx_bounce"] = {
    "title": _("Bounce buffers"),
    "color": "#4ef26c",
    "unit": "bytes",
}

metric_info["mem_lnx_writeback_tmp"] = {
    "title": _("Dirty FUSE data"),
    "color": "#4eeaf2",
    "unit": "bytes",
}

metric_info["mem_lnx_total_total"] = {
    "title": _("Total virtual memory"),
    "color": "#f0f0f0",
    "unit": "bytes",
}

metric_info["mem_lnx_committed_as"] = {
    "title": _("Committed memory"),
    "color": "#40a080",
    "unit": "bytes",
}

metric_info["mem_lnx_commit_limit"] = {
    "title": _("Commit limit"),
    "color": "#e0e0e0",
    "unit": "bytes",
}

metric_info["mem_lnx_shmem"] = {
    "title": _("Shared memory"),
    "color": "#bf9111",
    "unit": "bytes",
}

metric_info["mem_lnx_kernel_stack"] = {
    "title": _("Kernel stack"),
    "color": "#7192ad",
    "unit": "bytes",
}

metric_info["mem_lnx_page_tables"] = {
    "title": _("Page tables"),
    "color": "#71ad9f",
    "unit": "bytes",
}

metric_info["mem_lnx_mlocked"] = {
    "title": _("Locked mmap() data"),
    "color": "#a671ad",
    "unit": "bytes",
}

metric_info["mem_lnx_mapped"] = {
    "title": _("Mapped data"),
    "color": "#a671ad",
    "unit": "bytes",
}

metric_info["mem_lnx_anon_huge_pages"] = {
    "title": _("Anonymous huge pages"),
    "color": "#f0f0f0",
    "unit": "bytes",
}

metric_info["mem_lnx_huge_pages_total"] = {
    "title": _("Huge pages total"),
    "color": "#f0f0f0",
    "unit": "bytes",
}

metric_info["mem_lnx_huge_pages_free"] = {
    "title": _("Huge pages free"),
    "color": "#f0a0f0",
    "unit": "bytes",
}

metric_info["mem_lnx_huge_pages_rsvd"] = {
    "title": _("Huge pages reserved part of free"),
    "color": "#40f0f0",
    "unit": "bytes",
}

metric_info["mem_lnx_huge_pages_surp"] = {
    "title": _("Huge pages surplus"),
    "color": "#90f0b0",
    "unit": "bytes",
}

metric_info["mem_lnx_vmalloc_total"] = {
    "title": _("Total address space"),
    "color": "#f0f0f0",
    "unit": "bytes",
}

metric_info["mem_lnx_vmalloc_used"] = {
    "title": _("Allocated space"),
    "color": "#aaf76f",
    "unit": "bytes",
}

metric_info["mem_lnx_vmalloc_chunk"] = {
    "title": _("Largest free chunk"),
    "color": "#c6f7e9",
    "unit": "bytes",
}

metric_info["mem_lnx_hardware_corrupted"] = {
    "title": _("Hardware corrupted memory"),
    "color": "13/a",
    "unit": "bytes",
}

# Consumed Host Memory usage is defined as the amount of host memory that is allocated to the virtual machine
metric_info["mem_esx_host"] = {
    "title": _("Consumed host memory"),
    "color": "#70f038",
    "unit": "bytes",
}

# Active Guest Memory is defined as the amount of guest memory that is currently being used by the guest operating system and its applications
metric_info["mem_esx_guest"] = {
    "title": _("Active guest memory"),
    "color": "15/a",
    "unit": "bytes",
}

metric_info["mem_esx_ballooned"] = {
    "title": _("Ballooned memory"),
    "color": "21/a",
    "unit": "bytes",
}

metric_info["mem_esx_shared"] = {
    "title": _("Shared memory"),
    "color": "34/a",
    "unit": "bytes",
}

metric_info["mem_esx_private"] = {
    "title": _("Private memory"),
    "color": "25/a",
    "unit": "bytes",
}

metric_info["pagefile_total"] = {
    "title": _("Pagefile installed"),
    "color": "#e0e0e0",
    "unit": "bytes",
}

metric_info["load1"] = {
    "title": _("CPU load average of last minute"),
    "unit": "",
    "color": "34/c",
}

metric_info["load5"] = {
    "title": _("CPU load average of last 5 minutes"),
    "unit": "",
    "color": "#428399",
}

metric_info["load15"] = {
    "title": _("CPU load average of last 15 minutes"),
    "unit": "",
    "color": "#2c5766",
}

metric_info["predict_load15"] = {
    "title": _("Predicted average for 15 minute CPU load"),
    "unit": "",
    "color": "#a0b0c0",
}

metric_info["context_switches"] = {
    "title": _("Context switches"),
    "unit": "1/s",
    "color": "#80ff20",
}

metric_info["major_page_faults"] = {
    "title": _("Major page faults"),
    "unit": "1/s",
    "color": "#20ff80",
}

metric_info["page_swap_in"] = {
    "title": _("Page Swap In"),
    "unit": "1/s",
    "color": "33/a",
}

metric_info["page_swap_out"] = {
    "title": _("Page Swap Out"),
    "unit": "1/s",
    "color": "36/a",
}

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

metric_info["mem_heap"] = {
    "title": _("Heap memory usage"),
    "unit": "bytes",
    "color": "23/a",
}

metric_info["mem_heap_committed"] = {
    "title": _("Heap memory committed"),
    "unit": "bytes",
    "color": "23/b",
}

metric_info["mem_nonheap"] = {
    "title": _("Non-heap memory usage"),
    "unit": "bytes",
    "color": "16/a",
}

metric_info["mem_nonheap_committed"] = {
    "title": _("Non-heap memory committed"),
    "unit": "bytes",
    "color": "16/b",
}

metric_info["processes"] = {
    "title": _("Processes"),
    "unit": "count",
    "color": "#8040f0",
}

metric_info["threads"] = {
    "title": _("Threads"),
    "unit": "count",
    "color": "#8040f0",
}

metric_info["thread_usage"] = {
    "title": _("Thread usage"),
    "unit": "%",
    "color": "22/a",
}

metric_info["threads_idle"] = {
    "title": _("Idle threads"),
    "unit": "count",
    "color": "#8040f0",
}

metric_info["threads_rate"] = {
    "title": _("Thread creations per second"),
    "unit": "1/s",
    "color": "44/a",
}

metric_info["threads_daemon"] = {
    "title": _("Daemon threads"),
    "unit": "count",
    "color": "32/a",
}

metric_info["dedup_rate"] = {
    "title": _("Deduplication rate"),
    "unit": "count",
    "color": "12/a",
}

metric_info["threads_max"] = {
    "title": _("Maximum number of threads"),
    "help": _("Maximum number of threads started at any given time during the JVM lifetime"),
    "unit": "count",
    "color": "35/a",
}

metric_info["threads_total"] = {
    "title": _("Number of threads"),
    "unit": "count",
    "color": "41/a",
}

metric_info["threads_busy"] = {
    "title": _("Busy threads"),
    "unit": "count",
    "color": "34/a",
}

metric_info["5ghz_clients"] = {
    "title": _("Client connects for 5 Ghz Band"),
    "unit": "count",
    "color": "13/a",
}

metric_info["24ghz_clients"] = {
    "title": _("Client connects for 2,4 Ghz Band"),
    "unit": "count",
    "color": "14/a",
}

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

metric_info["vol_context_switches"] = {
    "title": _("Voluntary context switches"),
    "help": _("A voluntary context switch occurs when a thread blocks "
              "because it requires a resource that is unavailable"),
    "unit": "count",
    "color": "36/a",
}

metric_info["invol_context_switches"] = {
    "title": _("Involuntary context switches"),
    "help": _("An involuntary context switch takes place when a thread "
              "executes for the duration of its time slice or when the "
              "system identifies a higher-priority thread to run"),
    "unit": "count",
    "color": "45/b",
}

metric_info["tapes_total"] = {
    "title": _("Total number of tapes"),
    "unit": "count",
    "color": "36/a",
}

metric_info["tapes_free"] = {
    "title": _("Free tapes"),
    "unit": "count",
    "color": "45/b",
}

metric_info["tapes_util"] = {
    "title": _("Tape utilization"),
    "unit": "count",
    "color": "33/a",
}

metric_info["fs_free"] = {
    "title": _("Free filesystem space"),
    "unit": "bytes",
    "color": "#e3fff9",
}

metric_info["reserved"] = {
    "title": _("Reserved filesystem space"),
    "unit": "bytes",
    "color": "#ffcce6",
}

metric_info["fs_used"] = {
    "title": _("Used filesystem space"),
    "unit": "bytes",
    "color": "#00ffc6",
}

metric_info["fs_used_percent"] = {
    "title": _("Used filesystem space %"),
    "unit": "%",
    "color": "#00ffc6",
}

metric_info["inodes_used"] = {
    "title": _("Used inodes"),
    "unit": "count",
    "color": "#a0608f",
}

metric_info["fs_size"] = {
    "title": _("Filesystem size"),
    "unit": "bytes",
    "color": "#006040",
}

metric_info["fs_growth"] = {
    "title": _("Filesystem growth"),
    "unit": "bytes/d",
    "color": "#29cfaa",
}

metric_info["fs_trend"] = {
    "title": _("Trend of filesystem growth"),
    "unit": "bytes/d",
    "color": "#808080",
}

metric_info["fs_provisioning"] = {
    "title": _("Provisioned filesystem space"),
    "unit": "bytes",
    "color": "#ff8000",
}

metric_info["uncommitted"] = {
    "title": _("Uncommitted"),
    "unit": "bytes",
    "color": "16/a",
}

metric_info["overprovisioned"] = {
    "title": _("Overprovisioned"),
    "unit": "bytes",
    "color": "24/a",
}

metric_info["precompiled"] = {
    "title": _("Precompiled"),
    "unit": "bytes",
    "color": "16/a",
}

metric_info["temp"] = {
    "title": _("Temperature"),
    "unit": "c",
    "color": "16/a",
}

metric_info["cifs_share_users"] = {
    "title": _("Users using a cifs share"),
    "unit": "count",
    "color": "#60f020",
}

metric_info["smoke_ppm"] = {
    "title": _("Smoke"),
    "unit": "%/m",
    "color": "#60f088",
}

metric_info["smoke_perc"] = {
    "title": _("Smoke"),
    "unit": "%",
    "color": "#60f088",
}

metric_info["airflow"] = {
    "title": _("Air flow"),
    "unit": "l/s",
    "color": "#ff6234",
}

metric_info["fluidflow"] = {
    "title": _("Fluid flow"),
    "unit": "l/s",
    "color": "#ff6234",
}

metric_info["deviation_calibration_point"] = {
    "title": _("Deviation from calibration point"),
    "unit": "%",
    "color": "#60f020",
}

metric_info["deviation_airflow"] = {
    "title": _("Airflow deviation"),
    "unit": "%",
    "color": "#60f020",
}

metric_info["health_perc"] = {
    "title": _("Health"),
    "unit": "%",
    "color": "#ff6234",
}

# TODO: user -> cpu_util_user
metric_info["user"] = {
    "title": _("User"),
    "help": _("CPU time spent in user space"),
    "unit": "%",
    "color": "#60f020",
}

# metric_info["cpu_util_privileged"] = {
#     "title" : _("Privileged"),
#     "help"  : _("CPU time spent in privileged mode"),
#     "unit"  : "%",
#     "color" : "23/a",
# }

metric_info["nice"] = {
    "title": _("Nice"),
    "help": _("CPU time spent in user space for niced processes"),
    "unit": "%",
    "color": "#ff9050",
}

metric_info["interrupt"] = {
    "title": _("Interrupt"),
    "unit": "%",
    "color": "#ff9050",
}

metric_info["system"] = {
    "title": _("System"),
    "help": _("CPU time spent in kernel space"),
    "unit": "%",
    "color": "#ff6000",
}

metric_info["io_wait"] = {
    "title": _("I/O-wait"),
    "help": _("CPU time spent waiting for I/O"),
    "unit": "%",
    "color": "#00b0c0",
}

metric_info["cpu_util_guest"] = {
    "title": _("Guest operating systems"),
    "help": _("CPU time spent for executing guest operating systems"),
    "unit": "%",
    "color": "12/a",
}

metric_info["cpu_util_steal"] = {
    "title": _("Steal"),
    "help": _("CPU time stolen by other operating systems"),
    "unit": "%",
    "color": "16/a",
}

metric_info["idle"] = {
    "title": _("Idle"),
    "help": _("CPU idle time"),
    "unit": "%",
    "color": "#805022",
}

metric_info["fpga_util"] = {
    "title": _("FPGA utilization"),
    "unit": "%",
    "color": "#60f020",
}

metric_info["overall_util"] = {
    "title": _("Overall utilization"),
    "unit": "%",
    "color": "26/a",
}

metric_info["pci_io_util"] = {
    "title": _("PCI Express IO utilization"),
    "unit": "%",
    "color": "26/a",
}

metric_info["memory_util"] = {
    "title": _("Memory utilization"),
    "unit": "%",
    "color": "26/a",
}

metric_info["generic_util"] = {
    "title": _("Utilization"),
    "unit": "%",
    "color": "26/a",
}

metric_info["util"] = {
    "title": _("CPU utilization"),
    "unit": "%",
    "color": "26/a",
}

metric_info["util_numcpu_as_max"] = {
    "title": _("CPU utilization"),
    "unit": "%",
    "color": "#004080",
}

metric_info["util_average"] = {
    "title": _("CPU utilization (average)"),
    "unit": "%",
    "color": "44/a",
}

metric_info["util1s"] = {
    "title": _("CPU utilization last second"),
    "unit": "%",
    "color": "#50ff20",
}

metric_info["util5s"] = {
    "title": _("CPU utilization last five seconds"),
    "unit": "%",
    "color": "#600020",
}

metric_info["util1"] = {
    "title": _("CPU utilization last minute"),
    "unit": "%",
    "color": "#60f020",
}

metric_info["util5"] = {
    "title": _("CPU utilization last 5 minutes"),
    "unit": "%",
    "color": "#80f040",
}

metric_info["util15"] = {
    "title": _("CPU utilization last 15 minutes"),
    "unit": "%",
    "color": "#9a52bf",
}

metric_info["cpu_entitlement"] = {
    "title": _("Entitlement"),
    "unit": "",
    "color": "#77FF77",
}

metric_info["cpu_entitlement_util"] = {
    "title": _("Physical CPU consumption"),
    "unit": "",
    "color": "#FF0000",
}

for i in range(MAX_CORES):
    # generate different colors for each core.
    # unfortunately there are only 24 colors on our
    # color wheel, times two for two shades each, we
    # can only draw 48 differently colored graphs
    metric_info["cpu_core_util_%d" % i] = {
        "title": _("Utilization Core %d") % (i + 1),
        "unit": "%",
        "color": indexed_color(i, MAX_CORES),
    }

metric_info["time_offset"] = {
    "title": _("Time offset"),
    "unit": "s",
    "color": "#9a52bf",
}

metric_info["jitter"] = {
    "title": _("Time dispersion (jitter)"),
    "unit": "s",
    "color": "43/b",
}

metric_info["connection_time"] = {
    "title": _("Connection time"),
    "unit": "s",
    "color": "#94b65a",
}

metric_info["infections_rate"] = {
    "title": _("Infections"),
    "unit": "1/s",
    "color": "15/a",
}

metric_info["connections_blocked_rate"] = {
    "title": _("Blocked connections"),
    "unit": "1/s",
    "color": "14/a",
}

metric_info["connections_failed_rate"] = {
    "title": _("Failed connections"),
    "unit": "1/s",
    "color": "14/a",
}

metric_info["open_network_sockets"] = {
    "title": _("Open network sockets"),
    "unit": "count",
    "color": "21/a",
}

metric_info["connections"] = {
    "title": _("Connections"),
    "unit": "count",
    "color": "#a080b0",
}

metric_info["connections_ssl"] = {
    "title": _("SSL connections"),
    "unit": "count",
    "color": "13/a",
}

metric_info["connections_ssl_vpn"] = {
    "title": _("SSL/VPN connections"),
    "unit": "count",
    "color": "13/a",
}

metric_info["connections_async_writing"] = {
    "title": _("Asynchronous writing connections"),
    "unit": "count",
    "color": "16/a",
}

metric_info["connections_async_keepalive"] = {
    "title": _("Asynchronous keep alive connections"),
    "unit": "count",
    "color": "22/a",
}

metric_info["connections_async_closing"] = {
    "title": _("Asynchronous closing connections"),
    "unit": "count",
    "color": "24/a",
}

metric_info["connections_rate"] = {
    "title": _("Connections per second"),
    "unit": "1/s",
    "color": "#a080b0",
}

metric_info["connections_duration_min"] = {
    "title": _("Connections duration min"),
    "unit": "s",
    "color": "24/a"
}

metric_info["connections_duration_max"] = {
    "title": _("Connections duration max"),
    "unit": "s",
    "color": "25/a"
}

metric_info["connections_duration_mean"] = {
    "title": _("Connections duration max"),
    "unit": "s",
    "color": "25/a"
}

metric_info["packet_velocity_asic"] = {
    "title": _("Packet velocity asic"),
    "unit": "1/s",
    "color": "26/a"
}

metric_info["requests_per_second"] = {
    "title": _("Requests per second"),
    "unit": "1/s",
    "color": "#4080a0",
}

metric_info["input_signal_power_dbm"] = {
    "title": _("Input power"),
    "unit": "dbm",
    "color": "#20c080",
}

metric_info["output_signal_power_dbm"] = {
    "title": _("Output power"),
    "unit": "dbm",
    "color": "#2080c0",
}

metric_info["signal_power_dbm"] = {
    "title": _("Power"),
    "unit": "dbm",
    "color": "#2080c0",
}

metric_info["downstream_power"] = {
    "title": _("Downstream power"),
    "unit": "dbmv",
    "color": "14/a",
}

metric_info["current"] = {
    "title": _("Electrical current"),
    "unit": "a",
    "color": "#ffb030",
}

metric_info["differential_current_ac"] = {
    "title": _("Differential current AC"),
    "unit": "a",
    "color": "#ffb030",
}

metric_info["differential_current_dc"] = {
    "title": _("Differential current DC"),
    "unit": "a",
    "color": "#ffb030",
}

metric_info["voltage"] = {
    "title": _("Electrical voltage"),
    "unit": "v",
    "color": "14/a",
}

metric_info["power"] = {
    "title": _("Electrical power"),
    "unit": "w",
    "color": "22/a",
}

metric_info["appower"] = {
    "title": _("Electrical apparent power"),
    "unit": "va",
    "color": "22/b",
}

metric_info["energy"] = {
    "title": _("Electrical energy"),
    "unit": "wh",
    "color": "#aa80b0",
}

metric_info["output_load"] = {
    "title": _("Output load"),
    "unit": "%",
    "color": "#c83880",
}

metric_info["voltage_percent"] = {
    "title": _("Electrical tension in % of normal value"),
    "unit": "%",
    "color": "#ffc020",
}

metric_info["humidity"] = {
    "title": _("Relative humidity"),
    "unit": "%",
    "color": "#90b0b0",
}

metric_info["busy_workers"] = {
    "title": _("Busy workers"),
    "unit": "count",
    "color": "#a080b0",
}

metric_info["idle_workers"] = {
    "title": _("Idle workers"),
    "unit": "count",
    "color": "43/b",
}

metric_info["busy_servers"] = {
    "title": _("Busy servers"),
    "unit": "count",
    "color": "#a080b0",
}

metric_info["idle_servers"] = {
    "title": _("Idle servers"),
    "unit": "count",
    "color": "43/b",
}

metric_info["open_slots"] = {
    "title": _("Open slots"),
    "unit": "count",
    "color": "31/a",
}

metric_info["total_slots"] = {
    "title": _("Total slots"),
    "unit": "count",
    "color": "33/b",
}

metric_info["signal_noise"] = {
    "title": _("Signal/Noise ratio"),
    "unit": "db",
    "color": "#aadd66",
}

metric_info["noise_floor"] = {
    "title": _("Noise floor"),
    "unit": "dbm",
    "color": "11/a",
}

metric_info["codewords_corrected"] = {
    "title": _("Corrected codewords"),
    "unit": "%",
    "color": "#ff8040",
}

metric_info["codewords_uncorrectable"] = {
    "title": _("Uncorrectable codewords"),
    "unit": "%",
    "color": "#ff4020",
}

metric_info["total_sessions"] = {
    "title": _("Total sessions"),
    "unit": "count",
    "color": "#94b65a",
}

metric_info["running_sessions"] = {
    "title": _("Running sessions"),
    "unit": "count",
    "color": "42/a",
}

metric_info["rejected_sessions"] = {
    "title": _("Rejected sessions"),
    "unit": "count",
    "color": "45/a",
}

metric_info["active_sessions"] = {
    "title": _("Active sessions"),
    "unit": "count",
    "color": "11/a",
}

metric_info["inactive_sessions"] = {
    "title": _("Inactive sessions"),
    "unit": "count",
    "color": "13/a",
}

metric_info["session_rate"] = {
    "title": _("Session Rate"),
    "unit": "1/s",
    "color": "#4080a0",
}

metric_info["shared_locks"] = {
    "title": _("Shared locks"),
    "unit": "count",
    "color": "#92ec89",
}

metric_info["exclusive_locks"] = {
    "title": _("Exclusive locks"),
    "unit": "count",
    "color": "#ca5706",
}

metric_info["disk_read_throughput"] = {
    "title": _("Read throughput"),
    "unit": "bytes/s",
    "color": "#40c080",
}

metric_info["disk_write_throughput"] = {
    "title": _("Write throughput"),
    "unit": "bytes/s",
    "color": "#4080c0",
}

metric_info["disk_ios"] = {
    "title": _("Disk I/O operations"),
    "unit": "1/s",
    "color": "#60e0a0",
}

metric_info["disk_read_ios"] = {
    "title": _("Read operations"),
    "unit": "1/s",
    "color": "#60e0a0",
}

metric_info["disk_write_ios"] = {
    "title": _("Write operations"),
    "unit": "1/s",
    "color": "#60a0e0",
}

metric_info["disk_average_read_wait"] = {
    "title": _("Read wait time"),
    "unit": "s",
    "color": "#20e8c0",
}

metric_info["disk_min_read_wait"] = {
    "title": _("Minimum read wait time"),
    "unit": "s",
    "color": "#20e8a0",
}

metric_info["disk_max_read_wait"] = {
    "title": _("Maximum read wait time"),
    "unit": "s",
    "color": "#20e8e0",
}

metric_info["disk_average_write_wait"] = {
    "title": _("Write wait time"),
    "unit": "s",
    "color": "#20c0e8",
}

metric_info["disk_min_write_wait"] = {
    "title": _("Minimum write wait time"),
    "unit": "s",
    "color": "#20a0e8",
}

metric_info["disk_max_write_wait"] = {
    "title": _("Maximum write wait time"),
    "unit": "s",
    "color": "#20e0e8",
}

metric_info["disk_average_wait"] = {
    "title": _("Request wait time"),
    "unit": "s",
    "color": "#4488cc",
}

metric_info["disk_average_read_request_size"] = {
    "title": _("Average read request size"),
    "unit": "bytes",
    "color": "#409c58",
}

metric_info["disk_average_write_request_size"] = {
    "title": _("Average write request size"),
    "unit": "bytes",
    "color": "#40589c",
}

metric_info["disk_average_request_size"] = {
    "title": _("Average request size"),
    "unit": "bytes",
    "color": "#4488cc",
}

metric_info["disk_latency"] = {
    "title": _("Average disk latency"),
    "unit": "s",
    "color": "#c04080",
}

metric_info["disk_read_latency"] = {
    "title": _("Disk read latency"),
    "unit": "s",
    "color": "#40c080",
}

metric_info["disk_write_latency"] = {
    "title": _("Disk write latency"),
    "unit": "s",
    "color": "#4080c0",
}

metric_info["read_latency"] = {
    "title": _("Read latency"),
    "unit": "s",
    "color": "35/a",
}

metric_info["read_hits"] = {
    "title": _("Read hits"),
    "unit": "%",
    "color": "31/a",
}

metric_info["write_latency"] = {
    "title": _("Write latency"),
    "unit": "s",
    "color": "45/a",
}

metric_info["other_latency"] = {
    "title": _("Other latency"),
    "unit": "s",
    "color": "21/a",
}

metric_info["disk_queue_length"] = {
    "title": _("Average disk I/O-queue length"),
    "unit": "",
    "color": "35/a",
}

metric_info["disk_read_ql"] = {
    "title": _("Average disk read queue length"),
    "unit": "",
    "color": "45/a",
}

metric_info["disk_write_ql"] = {
    "title": _("Average disk write queue length"),
    "unit": "",
    "color": "#7060b0",
}

metric_info["disk_utilization"] = {
    "title": _("Disk utilization"),
    "unit": "%",
    "color": "#a05830",
}

metric_info["disk_capacity"] = {
    "title": _("Total disk capacity"),
    "unit": "bytes",
    "color": "12/a",
}

metric_info["disks"] = {
    "title": _("Disks"),
    "unit": "count",
    "color": "41/a",
}

metric_info["spare_disks"] = {
    "title": _("Spare disk"),
    "unit": "count",
    "color": "26/a",
}

metric_info["failed_disks"] = {
    "title": _("Failed disk"),
    "unit": "count",
    "color": "13/a",
}

metric_info["xda_hitratio"] = {
    "title": _("XDA hitratio"),
    "unit": "%",
    "color": "#0ae86d",
}

metric_info["data_hitratio"] = {
    "title": _("Data hitratio"),
    "unit": "%",
    "color": "#2828de",
}

metric_info["index_hitratio"] = {
    "title": _("Index hitratio"),
    "unit": "%",
    "color": "#dc359f",
}

metric_info["total_hitratio"] = {
    "title": _("Total hitratio"),
    "unit": "%",
    "color": "#2e282c",
}

metric_info["deadlocks"] = {
    "title": _("Deadlocks"),
    "unit": "1/s",
    "color": "#dc359f",
}

metric_info["lockwaits"] = {
    "title": _("Waitlocks"),
    "unit": "1/s",
    "color": "#2e282c",
}

metric_info["sort_overflow"] = {
    "title": _("Sort overflow"),
    "unit": "%",
    "color": "#e72121",
}

metric_info["hours_operation"] = {
    "title": _("Hours of operation"),
    "unit": "s",
    "color": "#94b65a",
}

metric_info["hours_since_service"] = {
    "title": _("Hours since service"),
    "unit": "s",
    "color": "#94b65a",
}

metric_info["execution_time"] = {
    "title": _("Total execution time"),
    "unit": "s",
    "color": "#d080af",
}

metric_info["user_time"] = {
    "title": _("CPU time in user space"),
    "unit": "s",
    "color": "#60f020",
}

metric_info["cpu_time_percent"] = {
    "title": _("CPU time"),
    "unit": "%",
    "color": "#94b65a",
}

metric_info["cpu_ready_percent"] = {
    "title": _("CPU ready"),
    "unit": "%",
    "color": "15/a",
}

metric_info["cpu_costop_percent"] = {
    "title": _("Co-Stop"),
    "unit": "%",
    "color": "11/a",
}

metric_info["system_time"] = {
    "title": _("CPU time in system space"),
    "unit": "s",
    "color": "#ff6000",
}

metric_info["children_user_time"] = {
    "title": _("Child time in user space"),
    "unit": "s",
    "color": "#aef090",
}

metric_info["children_system_time"] = {
    "title": _("Child time in system space"),
    "unit": "s",
    "color": "#ffb080",
}

metric_info["sync_latency"] = {
    "title": _("Sync latency"),
    "unit": "s",
    "color": "#ffb080",
}

metric_info["relay_log_space"] = {
    "title": _("Relay Log Size"),
    "unit": "bytes",
    "color": "#ffb080",
}

metric_info["mail_latency"] = {
    "title": _("Mail latency"),
    "unit": "s",
    "color": "#ffb080",
}

metric_info["printer_queue"] = {
    "title": _("Printer queue length"),
    "unit": "count",
    "color": "#a63df2",
}

metric_info["if_in_octets"] = {
    "title": _("Input Octets"),
    "unit": "bytes/s",
    "color": "#00e060",
}

metric_info["if_in_bps"] = {
    "title": _("Input bandwidth"),
    "unit": "bits/s",
    "color": "#00e060",
}

metric_info["if_in_pkts"] = {
    "title": _("Input Packets"),
    "unit": "1/s",
    "color": "#00e060",
}

metric_info["if_out_pkts"] = {
    "title": _("Output Packets"),
    "unit": "1/s",
    "color": "#0080e0",
}

metric_info["if_out_bps"] = {
    "title": _("Output bandwidth"),
    "unit": "bits/s",
    "color": "#0080e0",
}

metric_info["if_out_octets"] = {
    "title": _("Output Octets"),
    "unit": "bytes/s",
    "color": "#0080e0",
}

metric_info["if_in_discards"] = {
    "title": _("Input Discards"),
    "unit": "1/s",
    "color": "#ff8000",
}

metric_info["if_in_errors"] = {
    "title": _("Input Errors"),
    "unit": "1/s",
    "color": "#ff0000",
}

metric_info["if_out_discards"] = {
    "title": _("Output Discards"),
    "unit": "1/s",
    "color": "#ff8080",
}

metric_info["if_out_errors"] = {
    "title": _("Output Errors"),
    "unit": "1/s",
    "color": "#ff0080",
}

metric_info["if_in_unicast"] = {
    "title": _("Input unicast packets"),
    "unit": "1/s",
    "color": "#00ffc0",
}

metric_info["if_in_non_unicast"] = {
    "title": _("Input non-unicast packets"),
    "unit": "1/s",
    "color": "#00c080",
}

metric_info["if_out_unicast"] = {
    "title": _("Output unicast packets"),
    "unit": "1/s",
    "color": "#00c0ff",
}

metric_info["if_out_unicast_octets"] = {
    "title": _("Output unicast octets"),
    "unit": "bytes/s",
    "color": "#00c0ff",
}

metric_info["if_out_non_unicast"] = {
    "title": _("Output non-unicast packets"),
    "unit": "1/s",
    "color": "#0080c0",
}

metric_info["if_out_non_unicast_octets"] = {
    "title": _("Output non-unicast octets"),
    "unit": "bytes/s",
    "color": "#0080c0",
}

metric_info["p2s_bandwidth"] = {
    "title": _("Point-to-site bandwidth"),
    "unit": "bytes/s",
    "color": "#00c0ff",
}

metric_info["s2s_bandwidth"] = {
    "title": _("Site-to-site bandwidth"),
    "unit": "bytes/s",
    "color": "#00c080",
}

# “Output Queue Length is the length of the output packet queue (in
# packets). If this is longer than two, there are delays and the bottleneck
# should be found and eliminated, if possible.
metric_info["outqlen"] = {
    "title": _("Length of output queue"),
    "unit": "count",
    "color": "25/a",
}

metric_info["wlan_physical_errors"] = {
    "title": "WLAN physical errors",
    "unit": "1/s",
    "color": "14/a",
}

metric_info["wlan_resets"] = {
    "title": "WLAN Reset operations",
    "unit": "1/s",
    "color": "21/a",
}

metric_info["wlan_retries"] = {
    "title": "WLAN transmission retries",
    "unit": "1/s",
    "color": "24/a",
}

metric_info["read_blocks"] = {
    "title": _("Read blocks per second"),
    "unit": "1/s",
    "color": "11/a",
}

metric_info["write_blocks"] = {
    "title": _("Write blocks per second"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["broadcast_packets"] = {
    "title": _("Broadcast packets"),
    "unit": "1/s",
    "color": "11/a",
}

metric_info["multicast_packets"] = {
    "title": _("Multicast packets"),
    "unit": "1/s",
    "color": "14/a",
}

metric_info["fc_rx_bytes"] = {
    "title": _("Input"),
    "unit": "bytes/s",
    "color": "31/a",
}

metric_info["fc_tx_bytes"] = {
    "title": _("Output"),
    "unit": "bytes/s",
    "color": "35/a",
}

metric_info["fc_rx_frames"] = {
    "title": _("Received Frames"),
    "unit": "1/s",
    "color": "31/b",
}

metric_info["fc_tx_frames"] = {
    "title": _("Transmitted Frames"),
    "unit": "1/s",
    "color": "35/b",
}

metric_info["fc_rx_words"] = {
    "title": _("Received Words"),
    "unit": "1/s",
    "color": "26/b",
}

metric_info["fc_tx_words"] = {
    "title": _("Transmitted Words"),
    "unit": "1/s",
    "color": "31/b",
}

metric_info["fc_crc_errors"] = {
    "title": _("Receive CRC errors"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["fc_encouts"] = {
    "title": _("Enc-Outs"),
    "unit": "1/s",
    "color": "12/a",
}

metric_info["fc_encins"] = {
    "title": _("Enc-Ins"),
    "unit": "1/s",
    "color": "13/b",
}

metric_info["fc_bbcredit_zero"] = {
    "title": _("BBcredit zero"),
    "unit": "1/s",
    "color": "46/a",
}

metric_info["fc_c3discards"] = {
    "title": _("C3 discards"),
    "unit": "1/s",
    "color": "14/a",
}

metric_info["fc_notxcredits"] = {
    "title": _("No TX Credits"),
    "unit": "1/s",
    "color": "15/a",
}

metric_info["fc_c2c3_discards"] = {
    "title": _("C2 and c3 discards"),
    "unit": "1/s",
    "color": "15/a",
}

metric_info["fc_link_fails"] = {
    "title": _("Link failures"),
    "unit": "1/s",
    "color": "11/a",
}

metric_info["fc_sync_losses"] = {
    "title": _("Sync losses"),
    "unit": "1/s",
    "color": "12/a",
}

metric_info["fc_prim_seq_errors"] = {
    "title": _("Primitive sequence errors"),
    "unit": "1/s",
    "color": "13/a",
}

metric_info["fc_invalid_tx_words"] = {
    "title": _("Invalid TX words"),
    "unit": "1/s",
    "color": "14/a",
}

metric_info["fc_invalid_crcs"] = {
    "title": _("Invalid CRCs"),
    "unit": "1/s",
    "color": "15/a",
}

metric_info["fc_address_id_errors"] = {
    "title": _("Address ID errors"),
    "unit": "1/s",
    "color": "16/a",
}

metric_info["fc_link_resets_in"] = {
    "title": _("Link resets in"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["fc_link_resets_out"] = {
    "title": _("Link resets out"),
    "unit": "1/s",
    "color": "22/a",
}

metric_info["fc_offline_seqs_in"] = {
    "title": _("Offline sequences in"),
    "unit": "1/s",
    "color": "23/a",
}

metric_info["fc_offline_seqs_out"] = {
    "title": _("Offline sequences out"),
    "unit": "1/s",
    "color": "24/a",
}

metric_info["fc_c2_fbsy_frames"] = {
    "title": _("F_BSY frames"),
    "unit": "1/s",
    "color": "25/a",
}

metric_info["fc_c2_frjt_frames"] = {
    "title": _("F_RJT frames"),
    "unit": "1/s",
    "color": "26/a",
}

metric_info["rmon_packets_63"] = {
    "title": _("Packets of size 0-63 bytes"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["rmon_packets_127"] = {
    "title": _("Packets of size 64-127 bytes"),
    "unit": "1/s",
    "color": "24/a",
}

metric_info["rmon_packets_255"] = {
    "title": _("Packets of size 128-255 bytes"),
    "unit": "1/s",
    "color": "31/a",
}

metric_info["rmon_packets_511"] = {
    "title": _("Packets of size 256-511 bytes"),
    "unit": "1/s",
    "color": "34/a",
}

metric_info["rmon_packets_1023"] = {
    "title": _("Packets of size 512-1023 bytes"),
    "unit": "1/s",
    "color": "41/a",
}

metric_info["rmon_packets_1518"] = {
    "title": _("Packets of size 1024-1518 bytes"),
    "unit": "1/s",
    "color": "44/a",
}

metric_info["tcp_listen"] = {
    "title": _("State %s") % "LISTEN",
    "unit": "count",
    "color": "44/a",
}

metric_info["tcp_established"] = {
    "title": _("State %s") % "ESTABLISHED",
    "unit": "count",
    "color": "#00f040",
}

metric_info["tcp_syn_sent"] = {
    "title": _("State %s") % "SYN_SENT",
    "unit": "count",
    "color": "#a00000",
}

metric_info["tcp_syn_recv"] = {
    "title": _("State %s") % "SYN_RECV",
    "unit": "count",
    "color": "#ff4000",
}

metric_info["tcp_last_ack"] = {
    "title": _("State %s") % "LAST_ACK",
    "unit": "count",
    "color": "#c060ff",
}

metric_info["tcp_close_wait"] = {
    "title": _("State %s") % "CLOSE_WAIT",
    "unit": "count",
    "color": "#f000f0",
}

metric_info["tcp_time_wait"] = {
    "title": _("State %s") % "TIME_WAIT",
    "unit": "count",
    "color": "#00b0b0",
}

metric_info["tcp_closed"] = {
    "title": _("State %s") % "CLOSED",
    "unit": "count",
    "color": "#ffc000",
}

metric_info["tcp_closing"] = {
    "title": _("State %s") % "CLOSING",
    "unit": "count",
    "color": "#ffc080",
}

metric_info["tcp_fin_wait1"] = {
    "title": _("State %s") % "FIN_WAIT1",
    "unit": "count",
    "color": "#cccccc",
}

metric_info["tcp_fin_wait2"] = {
    "title": _("State %s") % "FIN_WAIT2",
    "unit": "count",
    "color": "#888888",
}

metric_info["tcp_bound"] = {
    "title": _("State %s") % "BOUND",
    "unit": "count",
    "color": "#4060a0",
}

metric_info["tcp_idle"] = {
    "title": _("State %s") % "IDLE",
    "unit": "count",
    "color": "41/a",
}

metric_info["fw_connections_active"] = {
    "title": _("Active connections"),
    "unit": "count",
    "color": "15/a",
}

metric_info["fw_connections_established"] = {
    "title": _("Established connections"),
    "unit": "count",
    "color": "41/a",
}

metric_info["fw_connections_halfopened"] = {
    "title": _("Half opened connections"),
    "unit": "count",
    "color": "16/a",
}

metric_info["fw_connections_halfclosed"] = {
    "title": _("Half closed connections"),
    "unit": "count",
    "color": "11/a",
}

metric_info["fw_connections_passthrough"] = {
    "title": _("Unoptimized connections"),
    "unit": "count",
    "color": "34/a",
}

metric_info["host_check_rate"] = {
    "title": _("Host check rate"),
    "unit": "1/s",
    "color": "52/a",
}

metric_info["monitored_hosts"] = {
    "title": _("Monitored hosts"),
    "unit": "count",
    "color": "52/b",
}

metric_info["hosts_active"] = {
    "title": _("Active hosts"),
    "unit": "count",
    "color": "11/a",
}

metric_info["hosts_inactive"] = {
    "title": _("Inactive hosts"),
    "unit": "count",
    "color": "16/a",
}

metric_info["hosts_degraded"] = {
    "title": _("Degraded hosts"),
    "unit": "count",
    "color": "23/a",
}

metric_info["hosts_offline"] = {
    "title": _("Offline hosts"),
    "unit": "count",
    "color": "31/a",
}

metric_info["hosts_other"] = {
    "title": _("Other hosts"),
    "unit": "count",
    "color": "41/a",
}

metric_info["service_check_rate"] = {
    "title": _("Service check rate"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["monitored_services"] = {
    "title": _("Monitored services"),
    "unit": "count",
    "color": "21/b",
}

metric_info["livestatus_connect_rate"] = {
    "title": _("Livestatus connects"),
    "unit": "1/s",
    "color": "#556677",
}

metric_info["livestatus_request_rate"] = {
    "title": _("Livestatus requests"),
    "unit": "1/s",
    "color": "#bbccdd",
}

metric_info["helper_usage_cmk"] = {
    "title": _("Check_MK helper usage"),
    "unit": "%",
    "color": "15/a",
}

metric_info["helper_usage_generic"] = {
    "title": _("Generic helper usage"),
    "unit": "%",
    "color": "41/a",
}

metric_info["average_latency_cmk"] = {
    "title": _("Check_MK check latency"),
    "unit": "s",
    "color": "15/a",
}

metric_info["average_latency_generic"] = {
    "title": _("Check latency"),
    "unit": "s",
    "color": "41/a",
}

metric_info["livestatus_usage"] = {
    "title": _("Livestatus usage"),
    "unit": "%",
    "color": "12/a",
}

metric_info["livestatus_overflows_rate"] = {
    "title": _("Livestatus overflows"),
    "unit": "1/s",
    "color": "16/a",
}

metric_info["cmk_time_agent"] = {
    "title": _("Time spent waiting for Check_MK agent"),
    "unit": "s",
    "color": "36/a",
}

metric_info["cmk_time_snmp"] = {
    "title": _("Time spent waiting for SNMP responses"),
    "unit": "s",
    "color": "32/a",
}

metric_info["cmk_time_ds"] = {
    "title": _("Time spent waiting for special agent"),
    "unit": "s",
    "color": "34/a",
}

# Note: current can be any phase, not only open, but also
# delayed, couting or ack.
metric_info["num_open_events"] = {
    "title": _("Current events"),
    "unit": "count",
    "color": "26/b",
}

metric_info["num_high_alerts"] = {
    "title": _("High alerts"),
    "unit": "count",
    "color": "22/a",
}

metric_info["num_disabled_alerts"] = {
    "title": _("Disabled alerts"),
    "unit": "count",
    "color": "24/a",
}

metric_info["average_message_rate"] = {
    "title": _("Incoming messages"),
    "unit": "1/s",
    "color": "23/a",
}

metric_info["average_drop_rate"] = {
    "title": _("Dropped messages"),
    "unit": "1/s",
    "color": "21/b",
}

metric_info["average_sync_time"] = {
    "title": _("Average slave sync time"),
    "unit": "s",
    "color": "46/a",
}

metric_info["average_rule_trie_rate"] = {
    "title": _("Rule tries"),
    "unit": "1/s",
    "color": "33/a",
}

metric_info["average_rule_hit_rate"] = {
    "title": _("Rule hits"),
    "unit": "1/s",
    "color": "34/b",
}

metric_info["average_event_rate"] = {
    "title": _("Event creations"),
    "unit": "1/s",
    "color": "31/a",
}

metric_info["average_connect_rate"] = {
    "title": _("Client connects"),
    "unit": "1/s",
    "color": "15/a",
}

metric_info["average_request_time"] = {
    "title": _("Average request response time"),
    "unit": "s",
    "color": "14/a",
}

metric_info["average_processing_time"] = {
    "title": _("Event processing time"),
    "unit": "s",
    "color": "13/a",
}

metric_info["average_rule_hit_ratio"] = {
    "title": _("Rule hit ratio"),
    "unit": "%",
    "color": "#cccccc",
}

metric_info["log_message_rate"] = {
    "title": _("Log messages"),
    "unit": "1/s",
    "color": "#aa44cc",
}

metric_info["normal_updates"] = {
    "title": _("Pending normal updates"),
    "unit": "count",
    "color": "#c08030",
}

metric_info["security_updates"] = {
    "title": _("Pending security updates"),
    "unit": "count",
    "color": "#ff0030",
}

metric_info["used_dhcp_leases"] = {
    "title": _("Used DHCP leases"),
    "unit": "count",
    "color": "#60bbbb",
}

metric_info["free_dhcp_leases"] = {
    "title": _("Free DHCP leases"),
    "unit": "count",
    "color": "34/a",
}

metric_info["pending_dhcp_leases"] = {
    "title": _("Pending DHCP leases"),
    "unit": "count",
    "color": "31/a",
}

metric_info["registered_phones"] = {
    "title": _("Registered phones"),
    "unit": "count",
    "color": "#60bbbb",
}

metric_info["messages"] = {
    "title": _("Messages"),
    "unit": "count",
    "color": "#aa44cc",
}

metric_info["call_legs"] = {
    "title": _("Call legs"),
    "unit": "count",
    "color": "#60bbbb",
}

metric_info["mails_received_time"] = {
    "title": _("Received mails"),
    "unit": "s",
    "color": "31/a",
}

metric_info["mail_queue_deferred_length"] = {
    "title": _("Length of deferred mail queue"),
    "unit": "count",
    "color": "#40a0b0",
}

metric_info["mail_queue_active_length"] = {
    "title": _("Length of active mail queue"),
    "unit": "count",
    "color": "#ff6000",
}

metric_info["mail_queue_deferred_size"] = {
    "title": _("Size of deferred mail queue"),
    "unit": "bytes",
    "color": "43/a",
}

metric_info["mail_queue_active_size"] = {
    "title": _("Size of active mail queue"),
    "unit": "bytes",
    "color": "31/a",
}

metric_info["messages_inbound"] = {
    "title": _("Inbound messages"),
    "unit": "1/s",
    "color": "31/a",
}

metric_info["messages_outbound"] = {
    "title": _("Outbound messages"),
    "unit": "1/s",
    "color": "36/a",
}

metric_info["pages_total"] = {
    "title": _("Total printed pages"),
    "unit": "count",
    "color": "46/a",
}

metric_info["pages_color"] = {
    "title": _("Color"),
    "unit": "count",
    "color": "#0010f4",
}

metric_info["pages_bw"] = {
    "title": _("B/W"),
    "unit": "count",
    "color": "51/a",
}

metric_info["pages_a4"] = {
    "title": _("A4"),
    "unit": "count",
    "color": "31/a",
}

metric_info["pages_a3"] = {
    "title": _("A3"),
    "unit": "count",
    "color": "31/b",
}

metric_info["pages_color_a4"] = {
    "title": _("Color A4"),
    "unit": "count",
    "color": "41/a",
}

metric_info["pages_bw_a4"] = {
    "title": _("B/W A4"),
    "unit": "count",
    "color": "51/b",
}

metric_info["pages_color_a3"] = {
    "title": _("Color A3"),
    "unit": "count",
    "color": "44/a",
}

metric_info["pages_bw_a3"] = {
    "title": _("B/W A3"),
    "unit": "count",
    "color": "52/a",
}

metric_info["pages"] = {
    "title": _("Remaining supply"),
    "unit": "count",
    "color": "34/a",
}

metric_info["supply_toner_cyan"] = {
    "title": _("Supply toner cyan"),
    "unit": "%",
    "color": "34/a",
}

metric_info["supply_toner_magenta"] = {
    "title": _("Supply toner magenta"),
    "unit": "%",
    "color": "12/a",
}

metric_info["supply_toner_yellow"] = {
    "title": _("Supply toner yellow"),
    "unit": "%",
    "color": "23/a",
}

metric_info["supply_toner_black"] = {
    "title": _("Supply toner black"),
    "unit": "%",
    "color": "51/a",
}

metric_info["supply_toner_other"] = {
    "title": _("Supply toner"),
    "unit": "%",
    "color": "52/a",
}

metric_info["pressure"] = {
    "title": _("Pressure"),
    "unit": "bar",
    "color": "#ff6234",
}

metric_info["pressure_pa"] = {
    "title": _("Pressure"),
    "unit": "pa",
    "color": "#ff6234",
}

metric_info["licenses"] = {
    "title": _("Used licenses"),
    "unit": "count",
    "color": "#ff6234",
}

metric_info["license_percentage"] = {
    "title": _("Used licenses"),
    "unit": "%",
    "color": "16/a",
}

metric_info["licenses_total"] = {
    "title": _("Total licenses"),
    "unit": "count",
    "color": "16/b",
}

metric_info["license_size"] = {
    "title": _("Size of license"),
    "unit": "bytes",
    "color": "11/a",
}

metric_info["license_usage"] = {
    "title": _("License usage"),
    "unit": "%",
    "color": "13/a",
}

metric_info["files_open"] = {
    "title": _("Open files"),
    "unit": "count",
    "color": "#ff6234",
}

metric_info["directories"] = {
    "title": _("Directories"),
    "unit": "count",
    "color": "#202020",
}

metric_info["shared_memory_segments"] = {
    "title": _("Shared memory segments"),
    "unit": "count",
    "color": "#606060",
}

metric_info["semaphore_ids"] = {
    "title": _("IPC semaphore IDs"),
    "unit": "count",
    "color": "#404040",
}

metric_info["semaphores"] = {
    "title": _("IPC semaphores"),
    "unit": "count",
    "color": "#ff4534",
}

metric_info["backup_size"] = {
    "title": _("Backup size"),
    "unit": "bytes",
    "color": "12/a",
}

metric_info["backup_avgspeed"] = {
    "title": _("Average speed of backup"),
    "unit": "bytes/s",
    "color": "22/a",
}

metric_info["backup_duration"] = {
    "title": _("Duration of backup"),
    "unit": "s",
    "color": "33/a",
}

metric_info["readsize"] = {
    "title": _("Readsize"),
    "unit": "bytes",
    "color": "12/a",
}

metric_info["transferredsize"] = {
    "title": _("Transferredsize"),
    "unit": "bytes",
    "color": "12/a",
}

metric_info["job_duration"] = {
    "title": _("Job duration"),
    "unit": "s",
    "color": "33/a",
}

metric_info["backup_age_database"] = {
    "title": _("Age of last database backup"),
    "unit": "s",
    "color": "11/a",
}

metric_info["backup_age_database_diff"] = {
    "title": _("Age of last differential database backup"),
    "unit": "s",
    "color": "14/a",
}

metric_info["backup_age_log"] = {
    "title": _("Age of last log backup"),
    "unit": "s",
    "color": "21/a",
}

metric_info["backup_age_file_or_filegroup"] = {
    "title": _("Age of last file or filegroup backup"),
    "unit": "s",
    "color": "24/a",
}

metric_info["backup_age_file_diff"] = {
    "title": _("Age of last differential file backup"),
    "unit": "s",
    "color": "31/a",
}

metric_info["backup_age_partial"] = {
    "title": _("Age of last partial backup"),
    "unit": "s",
    "color": "34/a",
}

metric_info["backup_age_differential_partial"] = {
    "title": _("Age of last differential partial backup"),
    "unit": "s",
    "color": "41/a",
}

metric_info["backup_age"] = {
    "title": _("Time since last backup"),
    "unit": "s",
    "color": "34/a",
}

metric_info["parts_per_million"] = {
    "color": "42/a",
    "title": _("Parts per Million"),
    "unit": "ppm",
}

metric_info["checkpoint_age"] = {
    "title": _("Time since last checkpoint"),
    "unit": "s",
    "color": "#006040",
}

metric_info["file_age_oldest"] = {
    "title": _("Oldest file"),
    "unit": "s",
    "color": "11/a",
}

metric_info["file_age_newest"] = {
    "title": _("Newest file"),
    "unit": "s",
    "color": "13/a",
}

metric_info["logswitches_last_hour"] = {
    "title": _("Log switches in the last 60 minutes"),
    "unit": "count",
    "color": "#006040",
}

metric_info["database_apply_lag"] = {
    "title": _("Database apply lag"),
    "help": _(
        "Amount of time that the application of redo data on the standby database lags behind the primary database"
    ),
    "unit": "s",
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

metric_info["jvm_garbage_collection_count"] = {
    "title": _("Garbage collections"),
    "unit": "1/s",
    "color": "31/a",
}

metric_info["jvm_garbage_collection_time"] = {
    "title": _("Time spent collecting garbage"),
    "unit": "%",
    "color": "32/a",
}

metric_info["net_data_recv"] = {
    "title": _("Net data received"),
    "unit": "bytes/s",
    "color": "41/b",
}

metric_info["net_data_sent"] = {
    "title": _("Net data sent"),
    "unit": "bytes/s",
    "color": "42/a",
}


def register_omd_apache_metrics():
    for ty, unit in [("requests", "1/s"), ("bytes", "bytes/s"), ("secs", "1/s")]:
        metric_info[ty + "_cmk_views"] = {
            "title": _("Check_MK: Views"),
            "unit": unit,
            "color": "#ff8080",
        }

        metric_info[ty + "_cmk_wato"] = {
            "title": _("Check_MK: WATO"),
            "unit": unit,
            "color": "#377cab",
        }

        metric_info[ty + "_cmk_bi"] = {
            "title": _("Check_MK: BI"),
            "unit": unit,
            "color": "#4eb0f2",
        }

        metric_info[ty + "_cmk_snapins"] = {
            "title": _("Check_MK: Snapins"),
            "unit": unit,
            "color": "#ff4040",
        }

        metric_info[ty + "_cmk_dashboards"] = {
            "title": _("Check_MK: Dashboards"),
            "unit": unit,
            "color": "#4040ff",
        }

        metric_info[ty + "_cmk_other"] = {
            "title": _("Check_MK: Other"),
            "unit": unit,
            "color": "#5bb9eb",
        }

        metric_info[ty + "_nagvis_snapin"] = {
            "title": _("NagVis: Snapin"),
            "unit": unit,
            "color": "#f2904e",
        }

        metric_info[ty + "_nagvis_ajax"] = {
            "title": _("NagVis: AJAX"),
            "unit": unit,
            "color": "#af91eb",
        }

        metric_info[ty + "_nagvis_other"] = {
            "title": _("NagVis: Other"),
            "unit": unit,
            "color": "#f2df40",
        }

        metric_info[ty + "_images"] = {
            "title": _("Image"),
            "unit": unit,
            "color": "#91cceb",
        }

        metric_info[ty + "_styles"] = {
            "title": _("Styles"),
            "unit": unit,
            "color": "#c6f24e",
        }

        metric_info[ty + "_scripts"] = {
            "title": _("Scripts"),
            "unit": unit,
            "color": "#4ef26c",
        }

        metric_info[ty + "_other"] = {
            "title": _("Other"),
            "unit": unit,
            "color": "#4eeaf2",
        }


register_omd_apache_metrics()

metric_info["total_modems"] = {
    "title": _("Total number of modems"),
    "unit": "count",
    "color": "12/c",
}

metric_info["active_modems"] = {
    "title": _("Active modems"),
    "unit": "count",
    "color": "14/c",
}

metric_info["registered_modems"] = {
    "title": _("Registered modems"),
    "unit": "count",
    "color": "16/c",
}

metric_info["registered_desktops"] = {
    "title": _("Registered desktops"),
    "unit": "count",
    "color": "16/d",
}

metric_info["channel_utilization"] = {
    "title": _("Channel utilization"),
    "unit": "%",
    "color": "24/c",
}

metric_info["frequency"] = {
    "title": _("Frequency"),
    "unit": "hz",
    "color": "11/c",
}

metric_info["battery_capacity"] = {
    "title": _("Battery capacity"),
    "unit": "%",
    "color": "11/c",
}

metric_info["battery_current"] = {
    "title": _("Battery electrical current"),
    "unit": "a",
    "color": "15/a",
}

metric_info["battery_temp"] = {
    "title": _("Battery temperature"),
    "unit": "c",
    "color": "#ffb030",
}

metric_info["connector_outlets"] = {
    "title": _("Connector outlets"),
    "unit": "count",
    "color": "51/a",
}

metric_info["qos_dropped_bytes_rate"] = {
    "title": _("QoS dropped bits"),
    "unit": "bits/s",
    "color": "41/a",
}

metric_info["qos_outbound_bytes_rate"] = {
    "title": _("QoS outbound bits"),
    "unit": "bits/s",
    "color": "26/a",
}

metric_info["apache_state_startingup"] = {
    "title": _("Starting up"),
    "unit": "count",
    "color": "11/a",
}

metric_info["apache_state_waiting"] = {
    "title": _("Waiting"),
    "unit": "count",
    "color": "14/a",
}

metric_info["apache_state_logging"] = {
    "title": _("Logging"),
    "unit": "count",
    "color": "21/a",
}

metric_info["apache_state_dns"] = {
    "title": _("DNS lookup"),
    "unit": "count",
    "color": "24/a",
}

metric_info["apache_state_sending_reply"] = {
    "title": _("Sending reply"),
    "unit": "count",
    "color": "31/a",
}

metric_info["apache_state_reading_request"] = {
    "title": _("Reading request"),
    "unit": "count",
    "color": "34/a",
}

metric_info["apache_state_closing"] = {
    "title": _("Closing connection"),
    "unit": "count",
    "color": "41/a",
}

metric_info["apache_state_idle_cleanup"] = {
    "title": _("Idle clean up of worker"),
    "unit": "count",
    "color": "44/a",
}

metric_info["apache_state_finishing"] = {
    "title": _("Gracefully finishing"),
    "unit": "count",
    "color": "46/b",
}

metric_info["apache_state_keep_alive"] = {
    "title": _("Keepalive"),
    "unit": "count",
    "color": "53/b",
}

metric_info["response_size"] = {
    "title": _("Response size"),
    "unit": "bytes",
    "color": "53/b",
}

metric_info["time_connect"] = {
    "title": _("Time to connect"),
    "unit": "s",
    "color": "11/a",
}

metric_info["time_ssl"] = {
    "title": _("Time to negotiate SSL"),
    "unit": "s",
    "color": "13/a",
}

metric_info["time_headers"] = {
    "title": _("Time to send request"),
    "unit": "s",
    "color": "15/a",
}

metric_info["time_firstbyte"] = {
    "title": _("Time to receive start of response"),
    "unit": "s",
    "color": "26/a",
}

metric_info["time_transfer"] = {
    "title": _("Time to receive full response"),
    "unit": "s",
    "color": "41/a",
}


def register_netapp_api_vs_traffic_metrics():
    for volume_info in ["NFS", "NFSv4", "NFSv4.1", "CIFS", "SAN", "FCP", "ISCSI"]:
        for what, unit in [
            ("data", "bytes"),
            ("latency", "s"),
            ("ios", "1/s"),
            ("throughput", "bytes/s"),
            ("ops", "1/s"),
        ]:
            volume = volume_info.lower().replace(".", "_")

            metric_info["%s_read_%s" % (volume, what)] = {
                "title": _("%s read %s") % (volume_info, what),
                "unit": unit,
                "color": "31/a",
            }

            metric_info["%s_write_%s" % (volume, what)] = {
                "title": _("%s write %s") % (volume_info, what),
                "unit": unit,
                "color": "44/a",
            }

            if what in ["data", "ops", "latency"]:
                metric_info["%s_other_%s" % (volume, what)] = {
                    "title": _("%s other %s") % (volume_info, what),
                    "unit": unit,
                    "color": "21/a",
                }


register_netapp_api_vs_traffic_metrics()

metric_info["nfs_ios"] = {
    "title": _("NFS operations"),
    "unit": "1/s",
    "color": "31/a",
}

metric_info["nfsv4_ios"] = {
    "title": _("NFSv4 operations"),
    "unit": "1/s",
    "color": "31/a",
}

metric_info["nfsv4_1_ios"] = {
    "title": _("NFSv4.1 operations"),
    "unit": "1/s",
    "color": "31/a",
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

metric_info["harddrive_uncorrectable_erros"] = {
    "title": _("Harddrive uncorrectable errors"),
    "unit": "count",
    "color": "44/a",
}

metric_info["harddrive_udma_crc_errors"] = {
    "title": _("Harddrive UDMA CRC errors"),
    "unit": "count",
    "color": "46/a",
}

metric_info["harddrive_crc_errors"] = {
    "title": _("Harddrive CRC errors"),
    "unit": "count",
    "color": "15/a",
}

metric_info["harddrive_uncorrectable_errors"] = {
    "title": _("Harddrive uncorrectable errors"),
    "unit": "count",
    "color": "13/a",
}

metric_info["nvme_media_and_data_integrity_errors"] = {
    "title": _("Media and data integrity errors"),
    "unit": "count",
    "color": "11/a",
}

metric_info["nvme_error_information_log_entries"] = {
    "title": _("Error information log entries"),
    "unit": "count",
    "color": "14/a",
}

metric_info["nvme_critical_warning"] = {
    "title": _("Critical warning"),
    "unit": "count",
    "color": "14/a",
}

metric_info["nvme_available_spare"] = {
    "title": _("Available Spare"),
    "unit": "%",
    "color": "21/a",
}

metric_info["nvme_spare_percentage_used"] = {
    "title": _("Percentage used"),
    "unit": "%",
    "color": "24/a",
}

metric_info["nvme_data_units_read"] = {
    "title": _("Data units read"),
    "unit": "bytes",
    "color": "31/a",
}

metric_info["nvme_data_units_written"] = {
    "title": _("Data units written"),
    "unit": "bytes",
    "color": "24/a",
}

metric_info["data_usage"] = {
    "title": _("Data usage"),
    "unit": "%",
    "color": "21/a",
}

metric_info["meta_usage"] = {
    "title": _("Meta usage"),
    "unit": "%",
    "color": "31/a",
}

metric_info["ap_devices_total"] = {
    "title": _("Total devices"),
    "unit": "count",
    "color": "51/a",
}

metric_info["ap_devices_drifted"] = {
    "title": _("Time drifted devices"),
    "unit": "count",
    "color": "23/a"
}

metric_info["ap_devices_not_responding"] = {
    "title": _("Not responding devices"),
    "unit": "count",
    "color": "14/a"
}

metric_info["request_rate"] = {
    "title": _("Request rate"),
    "unit": "1/s",
    "color": "34/a",
}

metric_info["error_rate"] = {
    "title": _("Error rate"),
    "unit": "1/s",
    "color": "14/a",
}

metric_info["citrix_load"] = {
    "title": _("Citrix Load"),
    "unit": "%",
    "color": "34/a",
}

metric_info["storage_processor_util"] = {
    "title": _("Storage Processor Utilization"),
    "unit": "%",
    "color": "34/a",
}

metric_info["storage_used"] = {
    "title": _("Storage space used"),
    "unit": "bytes",
    "color": "36/a",
}

metric_info["storage_percent"] = {
    "title": _("Storage space used"),
    "unit": "%",
    "color": "36/b",
}

metric_info["managed_object_count"] = {
    "title": _("Managed Objects"),
    "unit": "count",
    "color": "45/a"
}

metric_info["active_vpn_tunnels"] = {
    "title": _("Active VPN Tunnels"),
    "unit": "count",
    "color": "43/a"
}

metric_info["active_vpn_users"] = {
    "title": _("Active VPN Users"),
    "unit": "count",
    "color": "23/a",
}

metric_info["active_vpn_websessions"] = {
    "title": _("Active VPN Web Sessions"),
    "unit": "count",
    "color": "33/a"
}

metric_info["o2_percentage"] = {
    "title": _("Current O2 percentage"),
    "unit": "%",
    "color": "42/a",
}

metric_info["current_users"] = {
    "title": _("Current Users"),
    "unit": "count",
    "color": "23/a",
}

metric_info["average_latency"] = {
    "title": _("Average Latency"),
    "unit": "s",
    "color": "35/a",
}

metric_info["time_in_GC"] = {
    "title": _("Time spent in GC"),
    "unit": "%",
    "color": "16/a",
}

metric_info["db_read_latency"] = {
    "title": _("Read latency"),
    "unit": "s",
    "color": "35/a",
}

metric_info["db_read_recovery_latency"] = {
    "title": _("Read recovery latency"),
    "unit": "s",
    "color": "31/a",
}

metric_info["db_write_latency"] = {
    "title": _("Write latency"),
    "unit": "s",
    "color": "45/a",
}

metric_info["db_log_latency"] = {
    "title": _("Log latency"),
    "unit": "s",
    "color": "25/a",
}

metric_info["total_active_sessions"] = {
    "title": _("Total Active Sessions"),
    "unit": "count",
    "color": "#888888",
}

metric_info["tcp_active_sessions"] = {
    "title": _("Active TCP Sessions"),
    "unit": "count",
    "color": "#888800",
}

metric_info["udp_active_sessions"] = {
    "title": _("Active UDP sessions"),
    "unit": "count",
    "color": "#880088",
}

metric_info["icmp_active_sessions"] = {
    "title": _("Active ICMP Sessions"),
    "unit": "count",
    "color": "#008888"
}

metric_info["packages_accepted"] = {
    "title": _("Accepted Packages/s"),
    "unit": "1/s",
    "color": "#80ff40",
}
metric_info["packages_blocked"] = {
    "title": _("Blocked Packages/s"),
    "unit": "1/s",
    "color": "14/a",
}

metric_info["packages_icmp_total"] = {
    "title": _("ICMP Packages/s"),
    "unit": "count",
    "color": "21/a",
}

metric_info["sslproxy_active_sessions"] = {
    "title": _("Active SSL Proxy sessions"),
    "unit": "count",
    "color": "#11FF11",
}


def register_varnish_metrics():
    for what, descr, color in [
        ("busy", _("too many"), "11/a"),
        ("unhealthy", _("not attempted"), "13/a"),
        ("req", _("requests"), "15/a"),
        ("recycle", _("recycles"), "21/a"),
        ("retry", _("retry"), "23/a"),
        ("fail", _("failures"), "25/a"),
        ("toolate", _("was closed"), "31/a"),
        ("conn", _("success"), "33/a"),
        ("reuse", _("reuses"), "35/a"),
    ]:
        metric_info_key = "varnish_backend_%s_rate" % what
        metric_info[metric_info_key] = {
            "title": _("Backend Conn. %s") % descr,
            "unit": "1/s",
            "color": color,
        }

    for what, descr, color in [
        ("hit", _("hits"), "11/a"),
        ("miss", _("misses"), "13/a"),
        ("hitpass", _("hits for pass"), "21/a"),
    ]:
        metric_info_key = "varnish_cache_%s_rate" % what
        metric_info[metric_info_key] = {
            "title": _("Cache %s") % descr,
            "unit": "1/s",
            "color": color,
        }

    for what, descr, color in [
        ("drop", _("Connections dropped"), "12/a"),
        ("req", _("Client requests received"), "22/a"),
        ("conn", _("Client connections accepted"), "32/a"),
        ("drop_late", _("Connection dropped late"), "42/a"),
    ]:
        metric_info_key = "varnish_client_%s_rate" % what
        metric_info[metric_info_key] = {
            "title": descr,
            "unit": "1/s",
            "color": color,
        }

    for what, descr, color in [
        ("oldhttp", _("Fetch pre HTTP/1.1 closed"), "11/a"),
        ("head", _("Fetch head"), "13/a"),
        ("eof", _("Fetch EOF"), "15/a"),
        ("zero", _("Fetch zero length"), "21/a"),
        ("304", _("Fetch no body (304)"), "23/a"),
        ("1xx", _("Fetch no body (1xx)"), "25/a"),
        ("204", _("Fetch no body (204)"), "31/a"),
        ("length", _("Fetch with length"), "33/a"),
        ("failed", _("Fetch failed"), "35/a"),
        ("bad", _("Fetch had bad headers"), "41/a"),
        ("close", _("Fetch wanted close"), "43/a"),
        ("chunked", _("Fetch chunked"), "45/a"),
    ]:
        metric_info_key = "varnish_fetch_%s_rate" % what
        metric_info[metric_info_key] = {
            "title": descr,
            "unit": "1/s",
            "color": color,
        }

    for what, descr, color in [
        ("expired", _("Expired objects"), "21/a"),
        ("lru_nuked", _("LRU nuked objects"), "31/a"),
        ("lru_moved", _("LRU moved objects"), "41/a"),
    ]:
        metric_info_key = "varnish_objects_%s_rate" % what
        metric_info[metric_info_key] = {
            "title": descr,
            "unit": "1/s",
            "color": color,
        }

    for what, descr, color in [
        ("", _("Worker threads"), "11/a"),
        ("_lqueue", _("Work request queue length"), "13/a"),
        ("_create", _("Worker threads created"), "15/a"),
        ("_drop", _("Dropped work requests"), "21/a"),
        ("_failed", _("Worker threads not created"), "23/a"),
        ("_queued", _("Queued work requests"), "25/a"),
        ("_max", _("Worker threads limited"), "31/a"),
    ]:
        metric_info_key = "varnish_worker%s_rate" % what
        metric_info[metric_info_key] = {
            "title": descr,
            "unit": "1/s",
            "color": color,
        }


register_varnish_metrics()

# ESI = Edge Side Includes
metric_info["varnish_esi_errors_rate"] = {
    "title": _("ESI Errors"),
    "unit": "1/s",
    "color": "13/a",
}

metric_info["varnish_esi_warnings_rate"] = {
    "title": _("ESI Warnings"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["varnish_backend_success_ratio"] = {
    "title": _("Varnish Backend success ratio"),
    "unit": "%",
    "color": "#60c0c0",
}

metric_info["varnish_worker_thread_ratio"] = {
    "title": _("Varnish Worker thread ratio"),
    "unit": "%",
    "color": "#60c0c0",
}

metric_info["rx_light"] = {
    "title": _("RX Signal Power"),
    "unit": "dbm",
    "color": "35/a",
}

metric_info["tx_light"] = {
    "title": _("TX Signal Power"),
    "unit": "dbm",
    "color": "15/a",
}

for i in range(10):
    metric_info["rx_light_%d" % i] = {
        "title": _("RX Signal Power Lane %d") % (i + 1),
        "unit": "dbm",
        "color": "35/b",
    }
    metric_info["tx_light_%d" % i] = {
        "title": _("TX Signal Power Lane %d") % (i + 1),
        "unit": "dbm",
        "color": "15/b",
    }
    metric_info["port_temp_%d" % i] = {
        "title": _("Temperature Lane %d") % (i + 1),
        "unit": "dbm",
        "color": indexed_color(i * 3 + 2, 30),
    }

metric_info["locks_per_batch"] = {
    "title": _("Locks/Batch"),
    "unit": "",
    "color": "21/a",
}

metric_info["page_reads_sec"] = {
    "title": _("Page Reads"),
    "unit": "1/s",
    "color": "33/b",
}

metric_info["page_writes_sec"] = {
    "title": _("Page Writes"),
    "unit": "1/s",
    "color": "14/a",
}

metric_info["page_lookups_sec"] = {
    "title": _("Page Lookups"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["failed_search_requests"] = {
    "title": _("WEB - Failed search requests"),
    "unit": "1/s",
    "color": "42/a"
}

metric_info["failed_location_requests"] = {
    "title": _("WEB - Failed Get Locations Requests"),
    "unit": "1/s",
    "color": "42/a"
}

metric_info["failed_ad_requests"] = {
    "title": _("WEB - Timed out Active Directory Requests"),
    "unit": "1/s",
    "color": "42/a"
}

metric_info["http_5xx"] = {
    "title": _("HTTP 500 errors"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["sip_message_processing_time"] = {
    "title": _("SIP - Average Incoming Message Processing Time"),
    "unit": "s",
    "color": "42/a"
}

metric_info["asp_requests_rejected"] = {
    "title": _("ASP Requests Rejected"),
    "unit": "1/s",
    "color": "42/a"
}

metric_info["failed_file_requests"] = {
    "title": _("Failed File Requests"),
    "unit": "1/s",
    "color": "42/a"
}

metric_info["join_failures"] = {
    "title": _("Join Launcher Service Failures"),
    "unit": "count",
    "color": "42/a"
}

metric_info["failed_validate_cert_calls"] = {
    "title": _("WEB - Failed validate cert calls"),
    "unit": "count",
    "color": "42/a"
}

metric_info["sip_incoming_responses_dropped"] = {
    "title": _("SIP - Incoming Responses Dropped"),
    "unit": "1/s",
    "color": "42/a"
}

metric_info["sip_incoming_requests_dropped"] = {
    "title": _("SIP - Incoming Requests Dropped"),
    "unit": "1/s",
    "color": "42/a"
}

metric_info["usrv_queue_latency"] = {
    "title": _("USrv - Queue Latency"),
    "unit": "s",
    "color": "42/a"
}

metric_info["usrv_sproc_latency"] = {
    "title": _("USrv - Sproc Latency"),
    "unit": "s",
    "color": "42/a"
}

metric_info["usrv_throttled_requests"] = {
    "title": _("USrv - Throttled requests"),
    "unit": "1/s",
    "color": "42/a"
}

metric_info["sip_503_responses"] = {
    "title": _("SIP - Local 503 Responses"),
    "unit": "1/s",
    "color": "42/a"
}

metric_info["sip_incoming_messages_timed_out"] = {
    "title": _("SIP - Incoming Messages Timed out"),
    "unit": "count",
    "color": "42/a"
}

metric_info["caa_incomplete_calls"] = {
    "title": _("CAA - Incomplete Calls"),
    "unit": "1/s",
    "color": "42/a"
}

metric_info["usrv_create_conference_latency"] = {
    "title": _("USrv - Create Conference Latency"),
    "unit": "s",
    "color": "42/a"
}

metric_info["usrv_allocation_latency"] = {
    "title": _("USrv - Allocation Latency"),
    "unit": "s",
    "color": "42/a"
}

metric_info["sip_avg_holding_time_incoming_messages"] = {
    "title": _("SIP - Average Holding Time For Incoming Messages"),
    "unit": "s",
    "color": "42/a"
}

metric_info["sip_flow_controlled_connections"] = {
    "title": _("SIP - Flow-controlled Connections"),
    "unit": "count",
    "color": "42/a"
}

metric_info["sip_avg_outgoing_queue_delay"] = {
    "title": _("SIP - Average Outgoing Queue Delay"),
    "unit": "s",
    "color": "42/a"
}

metric_info["sip_sends_timed_out"] = {
    "title": _("SIP - Sends Timed-Out"),
    "unit": "1/s",
    "color": "42/a"
}

metric_info["sip_authentication_errors"] = {
    "title": _("SIP - Authentication Errors"),
    "unit": "1/s",
    "color": "42/a"
}

metric_info["mediation_load_call_failure_index"] = {
    "title": _("MediationServer - Load Call Failure Index"),
    "unit": "count",
    "color": "42/a"
}

metric_info["mediation_failed_calls_because_of_proxy"] = {
    "title": _("MediationServer - Failed calls caused by unexpected interaction from proxy"),
    "unit": "count",
    "color": "42/a"
}

metric_info["mediation_failed_calls_because_of_gateway"] = {
    "title": _("MediationServer - Failed calls caused by unexpected interaction from gateway"),
    "unit": "count",
    "color": "42/a"
}

metric_info["mediation_media_connectivity_failure"] = {
    "title": _("Mediation Server - Media Connectivity Check Failure"),
    "unit": "count",
    "color": "42/a"
}

metric_info["avauth_failed_requests"] = {
    "title": _("A/V Auth - Bad Requests Received"),
    "unit": "count",
    "color": "42/a"
}

metric_info["edge_udp_failed_auth"] = {
    "title": _("UDP Authentication Failures"),
    "unit": "1/s",
    "color": "42/a"
}

metric_info["edge_tcp_failed_auth"] = {
    "title": _("A/V Edge - TCP Authentication Failures"),
    "unit": "1/s",
    "color": "42/a"
}

metric_info["edge_udp_allocate_requests_exceeding_port_limit"] = {
    "title": _("A/V Edge - UDP Allocate Requests Exceeding Port Limit"),
    "unit": "1/s",
    "color": "42/a"
}

metric_info["edge_tcp_allocate_requests_exceeding_port_limit"] = {
    "title": _("A/V Edge - TCP Allocate Requests Exceeding Port Limit"),
    "unit": "1/s",
    "color": "42/a"
}

metric_info["edge_udp_packets_dropped"] = {
    "title": _("A/V Edge - UDP Packets Dropped"),
    "unit": "1/s",
    "color": "42/a"
}

metric_info["edge_tcp_packets_dropped"] = {
    "title": _("A/V Edge - TCP Packets Dropped"),
    "unit": "1/s",
    "color": "42/a"
}

metric_info["tcp_packets_received"] = {
    "title": _("Received TCP packets"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["udp_packets_received"] = {
    "title": _("Received UDP packets"),
    "unit": "1/s",
    "color": "23/a",
}

metric_info["icmp_packets_received"] = {
    "title": _("Received ICMP packets"),
    "unit": "1/s",
    "color": "25/a",
}

metric_info["dataproxy_connections_throttled"] = {
    "title": _("DATAPROXY - Throttled Server Connections"),
    "unit": "count",
    "color": "42/a"
}

metric_info["xmpp_failed_outbound_streams"] = {
    "title": _("XmppFederationProxy - Failed outbound stream establishes"),
    "unit": "1/s",
    "color": "26/a",
}

metric_info["xmpp_failed_inbound_streams"] = {
    "title": _("XmppFederationProxy - Failed inbound stream establishes"),
    "unit": "1/s",
    "color": "31/a",
}

skype_mobile_devices = [
    ("android", "Android", "33/a"),
    ("iphone", "iPhone", "42/a"),
    ("ipad", "iPad", "45/a"),
    ("mac", "Mac", "23/a"),
]


def register_skype_mobile_metrics():
    for device, name, color in skype_mobile_devices:
        metric_info["ucwa_active_sessions_%s" % device] = {
            "title": _("UCWA - Active Sessions (%s)") % name,
            "unit": "count",
            "color": color
        }


register_skype_mobile_metrics()

metric_info["web_requests_processing"] = {
    "title": _("WEB - Requests in Processing"),
    "unit": "count",
    "color": "12/a"
}


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

metric_info["dhcp_discovery"] = {
    "title": _("DHCP Discovery messages"),
    "unit": "count",
    "color": "11/a",
}

metric_info["dhcp_requests"] = {
    "title": _("DHCP received requests"),
    "unit": "count",
    "color": "14/a",
}

metric_info["dhcp_releases"] = {
    "title": _("DHCP received releases"),
    "unit": "count",
    "color": "21/a",
}

metric_info["dhcp_declines"] = {
    "title": _("DHCP received declines"),
    "unit": "count",
    "color": "24/a",
}

metric_info["dhcp_informs"] = {
    "title": _("DHCP received informs"),
    "unit": "count",
    "color": "31/a",
}

metric_info["dhcp_others"] = {
    "title": _("DHCP received other messages"),
    "unit": "count",
    "color": "34/a",
}

metric_info["dhcp_offers"] = {
    "title": _("DHCP sent offers"),
    "unit": "count",
    "color": "12/a",
}

metric_info["dhcp_acks"] = {
    "title": _("DHCP sent acks"),
    "unit": "count",
    "color": "15/a",
}

metric_info["dhcp_nacks"] = {
    "title": _("DHCP sent nacks"),
    "unit": "count",
    "color": "22/b",
}

metric_info["dns_successes"] = {
    "title": _("DNS successful responses"),
    "unit": "count",
    "color": "11/a",
}

metric_info["dns_referrals"] = {
    "title": _("DNS referrals"),
    "unit": "count",
    "color": "14/a",
}

metric_info["dns_recursion"] = {
    "title": _("DNS queries received using recursion"),
    "unit": "count",
    "color": "21/a",
}

metric_info["dns_failures"] = {
    "title": _("DNS failed queries"),
    "unit": "count",
    "color": "24/a",
}

metric_info["dns_nxrrset"] = {
    "title": _("DNS queries received for non-existent record"),
    "unit": "count",
    "color": "31/a",
}

metric_info["dns_nxdomain"] = {
    "title": _("DNS queries received for non-existent domain"),
    "unit": "count",
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

metric_info["fan"] = {
    "title": _("Fan speed"),
    "unit": "rpm",
    "color": "16/b",
}

metric_info["fan_perc"] = {
    "title": _("Fan speed"),
    "unit": "%",
    "color": "16/b",
}

metric_info["inside_macs"] = {
    "title": _("Number of unique inside MAC addresses"),
    "unit": "count",
    "color": "31/a",
}

metric_info["outside_macs"] = {
    "title": _("Number of unique outside MAC addresses"),
    "unit": "count",
    "color": "33/a",
}

# EMC VNX storage pools metrics
metric_info["emcvnx_consumed_capacity"] = {
    "title": _("Consumed capacity"),
    "unit": "bytes",
    "color": "13/a",
}

metric_info["emcvnx_avail_capacity"] = {
    "title": _("Available capacity"),
    "unit": "bytes",
    "color": "21/a",
}

metric_info["emcvnx_over_subscribed"] = {
    "title": _("Oversubscribed"),
    "unit": "bytes",
    "color": "13/a",
}

metric_info["emcvnx_total_subscribed_capacity"] = {
    "title": _("Total subscribed capacity"),
    "unit": "bytes",
    "color": "31/a",
}

metric_info["emcvnx_perc_full"] = {
    "title": _("Percent full"),
    "unit": "%",
    "color": "11/a",
}

metric_info["emcvnx_perc_subscribed"] = {
    "title": _("Percent subscribed"),
    "unit": "%",
    "color": "21/a",
}

metric_info["emcvnx_move_up"] = {
    "title": _("Data to move up"),
    "unit": "bytes",
    "color": "11/a",
}

metric_info["emcvnx_move_down"] = {
    "title": _("Data to move down"),
    "unit": "bytes",
    "color": "21/a",
}

metric_info["emcvnx_move_within"] = {
    "title": _("Data to move within"),
    "unit": "bytes",
    "color": "31/a",
}

metric_info["emcvnx_move_completed"] = {
    "title": _("Data movement completed"),
    "unit": "bytes",
    "color": "41/a",
}

metric_info["emcvnx_targeted_higher"] = {
    "title": _("Data targeted for higher tier"),
    "unit": "bytes",
    "color": "11/a",
}

metric_info["emcvnx_targeted_lower"] = {
    "title": _("Data targeted for lower tier"),
    "unit": "bytes",
    "color": "21/a",
}

metric_info["emcvnx_targeted_within"] = {
    "title": _("Data targeted for within tier"),
    "unit": "bytes",
    "color": "31/a",
}

metric_info["emcvnx_time_to_complete"] = {
    "title": _("Estimated time to complete"),
    "unit": "s",
    "color": "31/a",
}

metric_info["emcvnx_dedupl_perc_completed"] = {
    "title": _("Deduplication percent completed"),
    "unit": "%",
    "color": "11/a",
}

metric_info["emcvnx_dedupl_efficiency_savings"] = {
    "title": _("Deduplication efficiency savings"),
    "unit": "bytes",
    "color": "11/a",
}

metric_info["emcvnx_dedupl_remaining_size"] = {
    "title": _("Deduplication remaining size"),
    "unit": "bytes",
    "color": "21/a",
}

metric_info["emcvnx_dedupl_shared_capacity"] = {
    "title": _("Deduplication shared capacity"),
    "unit": "bytes",
    "color": "31/a",
}

metric_info["docker_all_containers"] = {
    "title": _("Number of containers"),
    "unit": "count",
    "color": "43/a",
}

metric_info["docker_running_containers"] = {
    "title": _("Running containers"),
    "unit": "count",
    "color": "31/a",
}

metric_info["ready_containers"] = {
    "title": _("Ready containers"),
    "unit": "count",
    "color": "23/a",
}

metric_info["docker_paused_containers"] = {
    "title": _("Paused containers"),
    "unit": "count",
    "color": "24/a",
}

metric_info["docker_stopped_containers"] = {
    "title": _("Stopped containers"),
    "unit": "count",
    "color": "14/a",
}

metric_info["docker_count"] = {
    "title": _("Count"),
    "unit": "count",
    "color": "11/a",
}

metric_info["docker_active"] = {
    "title": _("Active"),
    "unit": "count",
    "color": "21/a",
}

metric_info["docker_size"] = {
    "title": _("Size"),
    "unit": "bytes",
    "color": "41/a",
}

metric_info["docker_reclaimable"] = {
    "title": _("Reclaimable"),
    "unit": "bytes",
    "color": "31/a",
}

metric_info["k8s_nodes"] = {
    "title": _("Nodes"),
    "unit": "count",
    "color": "11/a",
}

metric_info["k8s_pods_request"] = {
    "title": _("Pods"),
    "unit": "count",
    "color": "16/b",
}

metric_info["k8s_pods_allocatable"] = {
    "title": _("Allocatable"),
    "unit": "count",
    "color": "#e0e0e0",
}

metric_info["k8s_pods_capacity"] = {
    "title": _("Capacity"),
    "unit": "count",
    "color": "c0c0c0",
}

metric_info["k8s_cpu_request"] = {
    "title": _("Request"),
    "unit": "",
    "color": "26/b",
}

metric_info["k8s_cpu_limit"] = {
    "title": _("Limit"),
    "unit": "",
    "color": "26/a",
}

metric_info["k8s_cpu_allocatable"] = {
    "title": _("Allocatable"),
    "unit": "",
    "color": "#e0e0e0",
}

metric_info["k8s_cpu_capacity"] = {
    "title": _("Capacity"),
    "unit": "",
    "color": "#c0c0c0",
}

metric_info["k8s_memory_request"] = {
    "title": _("Request"),
    "unit": "bytes",
    "color": "42/b",
}

metric_info["k8s_memory_limit"] = {
    "title": _("Limit"),
    "unit": "bytes",
    "color": "42/a",
}

metric_info["k8s_memory_allocatable"] = {
    "title": _("Allocatable"),
    "unit": "bytes",
    "color": "#e0e0e0",
}

metric_info["k8s_memory_capacity"] = {
    "title": _("Capacity"),
    "unit": "bytes",
    "color": "#c0c0c0",
}

metric_info["k8s_pods_usage"] = {
    "title": _("Pod request"),
    "unit": "%",
    "color": "31/a",
}

metric_info["k8s_memory_usage"] = {
    "title": _("Memory request"),
    "unit": "%",
    "color": "31/a",
}

metric_info["k8s_cpu_usage"] = {
    "title": _("CPU request"),
    "unit": "%",
    "color": "31/a",
}

metric_info["k8s_total_roles"] = {
    "title": _("Total"),
    "unit": "",
    "color": "31/a",
}

metric_info["k8s_cluster_roles"] = {
    "title": _("Cluster roles"),
    "unit": "",
    "color": "21/a",
}

metric_info["k8s_roles"] = {
    "title": _("Roles"),
    "unit": "",
    "color": "21/b",
}

metric_info["k8s_daemon_pods_ready"] = {
    "title": _("Number of nodes ready"),
    "unit": "",
    "color": "23/a",
}

metric_info["k8s_daemon_pods_scheduled_desired"] = {
    "title": _("Desired number of nodes scheduled"),
    "unit": "",
    "color": "21/a",
}

metric_info["k8s_daemon_pods_scheduled_current"] = {
    "title": _("Current number of nodes scheduled"),
    "unit": "",
    "color": "31/a",
}

metric_info["k8s_daemon_pods_scheduled_updated"] = {
    "title": _("Number of nodes scheduled with up-to-date pods"),
    "unit": "",
    "color": "22/a",
}

metric_info["k8s_daemon_pods_available"] = {
    "title": _("Number of nodes scheduled with available pods"),
    "unit": "",
    "color": "35/a",
}

metric_info["k8s_daemon_pods_unavailable"] = {
    "title": _("Number of nodes scheduled with unavailable pods"),
    "unit": "",
    "color": "14/a",
}

metric_info["ready_replicas"] = {
    "title": _("Ready replicas"),
    "unit": "",
    "color": "21/a",
}

metric_info["total_replicas"] = {
    "title": _("Total replicas"),
    "unit": "",
    "color": "35/a",
}

metric_info["active_vms"] = {
    "title": _("Active VMs"),
    "unit": "count",
    "color": "14/a",
}

metric_info["quarantine"] = {
    "title": _("Quarantine Usage"),
    "unit": "%",
    "color": "43/b",
}

metric_info["messages_in_queue"] = {
    "title": _("Messages in queue"),
    "unit": "count",
    "color": "16/a",
}

metric_info["mail_queue_hold_length"] = {
    "title": _("Length of hold mail queue"),
    "unit": "count",
    "color": "26/b",
}

metric_info["mail_queue_incoming_length"] = {
    "title": _("Length of incoming mail queue"),
    "unit": "count",
    "color": "14/b",
}

metric_info["mail_queue_drop_length"] = {
    "title": _("Length of drop mail queue"),
    "unit": "count",
    "color": "51/b",
}

metric_info["mail_received_rate"] = {
    "title": _("Mails received rate"),
    "unit": "1/s",
    "color": "31/a",
}


def register_fireye_metrics():
    for what, color in [
        ('Total', '14/b'),
        ('Infected', '53/b'),
        ('Analyzed', '23/a'),
        ('Bypass', '13/b'),
    ]:
        metric_info_key = '%s_rate' % what.lower()
        metric_info[metric_info_key] = {
            'title': _('%s per Second') % what,
            'unit': '1/s',
            'color': color,
        }

    for what, color in [
        ('Attachment', '14/b'),
        ('URL', '13/b'),
        ('Malicious Attachment', '23/a'),
        ('Malicious URL', '53/b'),
    ]:
        metric_info_key = 'fireeye_stat_%s' % what.replace(' ', '').lower()
        metric_info[metric_info_key] = {
            'title': _('Emails containing %s per Second') % what,
            'unit': '1/s',
            'color': color,
        }


register_fireye_metrics()

metric_info["queue"] = {
    "title": _("Queue length"),
    "unit": "count",
    "color": "42/a",
}

metric_info["avg_response_time"] = {
    "title": _("Average response time"),
    "unit": "s",
    "color": "#4040ff",
}

metric_info["remaining_reads"] = {
    "title": _("Remaining Reads"),
    "unit": "count",
    "color": "42/a",
}

metric_info["dtu_percent"] = {
    "title": _("Database throughput unit"),
    "unit": "%",
    "color": "#4040ff"
}

metric_info["connections_max_used"] = {
    "title": _("Maximum used parallel connections"),
    "unit": "count",
    "color": "42/a",
}

metric_info["connections_max"] = {
    "title": _("Maximum parallel connections"),
    "unit": "count",
    "color": "51/b",
}

metric_info["connections_perc_used"] = {
    "title": _("Parallel connections load"),
    "unit": "%",
    "color": "21/a",
}

metric_info['op_s'] = {
    'title': _('Operations per second'),
    'unit': 'count',
    'color': '#90ee90',
}

metric_info['rpc_backlog'] = {
    'title': _('RPC Backlog'),
    'unit': 'count',
    'color': '#90ee90',
}

metric_info['read_ops'] = {
    'title': _('Read operations'),
    'unit': '1/s',
    'color': '34/a',
}

metric_info['read_b_s'] = {
    'title': _('Read size per second'),
    'unit': 'bytes/s',
    'color': '#80ff20',
}

metric_info['read_b_op'] = {
    'title': _('Read size per operation'),
    'unit': 'bytes/op',
    'color': '#4080c0',
    "render": cmk.utils.render.fmt_bytes,
}

metric_info['read_retrans'] = {
    'title': _('Read retransmission'),
    'unit': '%',
    'color': '#90ee90',
}

metric_info['read_avg_rtt_ms'] = {
    'title': _('Read average rtt'),
    'unit': 's',
    'color': '#90ee90',
}

metric_info['read_avg_exe_ms'] = {
    'title': _('Read average exe'),
    'unit': 's',
    'color': '#90ee90',
}

metric_info['write_ops_s'] = {
    'title': _('Write operations'),
    'unit': '1/s',
    'color': '34/a',
}

metric_info['write_b_s'] = {
    'title': _('Writes size per second'),
    'unit': 'bytes/s',
    'color': '#80ff20',
}

metric_info['write_b_op'] = {
    'title': _('Writes size per operation'),
    'unit': 'bytes/op',
    'color': '#4080c0',
    "render": cmk.utils.render.fmt_bytes,
}

metric_info['write_avg_rtt_ms'] = {
    'title': _('Write average rtt'),
    'unit': 's',
    'color': '#90ee90',
}

metric_info['write_avg_exe_ms'] = {
    'title': _('Write average exe'),
    'unit': 's',
    'color': '#90ee90',
}

metric_info['aws_costs_unblended'] = {
    'title': _('Unblended costs'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_glacier_number_of_vaults'] = {
    'title': _('Number of vaults'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_glacier_num_archives'] = {
    'title': _('Number of archives'),
    'unit': 'count',
    'color': '21/a',
}

metric_info['aws_glacier_vault_size'] = {
    'title': _('Vault size'),
    'unit': 'bytes',
    'color': '15/a',
}

metric_info['aws_glacier_total_vault_size'] = {
    'title': _('Total size of all vaults'),
    'unit': 'bytes',
    'color': '15/a',
}

metric_info['aws_glacier_largest_vault_size'] = {
    'title': _('Largest vault size'),
    'unit': 'bytes',
    'color': '21/a',
}

metric_info['aws_num_objects'] = {
    'title': _('Number of objects'),
    'unit': 'count',
    'color': '21/a',
}

metric_info['aws_bucket_size'] = {
    'title': _('Bucket size'),
    'unit': 'bytes',
    'color': '15/a',
}

metric_info['aws_largest_bucket_size'] = {
    'title': _('Largest bucket size'),
    'unit': 'bytes',
    'color': '21/a',
}

metric_info['aws_surge_queue_length'] = {
    'title': _('Surge queue length'),
    'unit': 'count',
    'color': '12/a',
}

metric_info['aws_spillover'] = {
    'title': _('The number of requests that were rejected (spillover)'),
    'unit': 'count',
    'color': '13/a',
}

metric_info["aws_load_balancer_latency"] = {
    "title": _("Load balancer latency"),
    "unit": "s",
    "color": "21/a",
}

metric_info["aws_http_4xx_rate"] = {
    "title": _("HTTP 400 errors"),
    "unit": "1/s",
    "color": "32/a",
}

metric_info["aws_http_5xx_rate"] = {
    "title": _("HTTP 500 errors"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["aws_http_4xx_perc"] = {
    "title": _("Percentage of HTTP 400 errors"),
    "unit": "%",
    "color": "32/a",
}

metric_info["aws_http_5xx_perc"] = {
    "title": _("Percentage of HTTP 500 errors"),
    "unit": "%",
    "color": "42/a",
}

metric_info["aws_overall_hosts_health_perc"] = {
    "title": _("Proportion of healthy host"),
    "unit": "%",
    "color": "35/a",
}

metric_info['aws_backend_connection_errors_rate'] = {
    'title': _('Backend connection errors'),
    'unit': '1/s',
    'color': '15/a',
}

metric_info['aws_burst_balance'] = {
    'title': _('Burst Balance'),
    'unit': '%',
    'color': '11/a',
}

metric_info['aws_cpu_credit_balance'] = {
    'title': _('CPU Credit Balance'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_rds_bin_log_disk_usage'] = {
    'title': _('Bin Log Disk Usage'),
    'unit': '%',
    'color': '11/a',
}

metric_info['aws_rds_transaction_logs_disk_usage'] = {
    'title': _('Transaction Logs Disk Usage'),
    'unit': '%',
    'color': '12/a',
}

metric_info['aws_rds_replication_slot_disk_usage'] = {
    'title': _('Replication Slot Disk Usage'),
    'unit': '%',
    'color': '13/a',
}

metric_info['aws_rds_oldest_replication_slot_lag'] = {
    'title': _('Oldest Replication Slot Lag Size'),
    'unit': 'bytes',
    'color': '14/a',
}

metric_info['aws_rds_connections'] = {
    'title': _('Connections in use'),
    'unit': 'count',
    'color': '21/a',
}

metric_info['aws_request_latency'] = {
    'title': _('Request latency'),
    'unit': 's',
    'color': '21/a',
}

metric_info['aws_ec2_vpc_elastic_ip_addresses'] = {
    'title': _('VPC Elastic IP Addresses'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_ec2_elastic_ip_addresses'] = {
    'title': _('Elastic IP Addresses'),
    'unit': 'count',
    'color': '13/a',
}

metric_info['aws_ec2_spot_inst_requests'] = {
    'title': _('Spot Instance Requests'),
    'unit': 'count',
    'color': '15/a',
}

metric_info['aws_ec2_active_spot_fleet_requests'] = {
    'title': _('Active Spot Fleet Requests'),
    'unit': 'count',
    'color': '21/a',
}

metric_info['aws_ec2_spot_fleet_total_target_capacity'] = {
    'title': _('Spot Fleet Requests Total Target Capacity'),
    'unit': 'count',
    'color': '23/a',
}

metric_info['aws_ec2_running_ondemand_instances_total'] = {
    'title': _('Total running On-Demand Instances'),
    'unit': 'count',
    'color': '#000000',
}

for i, inst_type in enumerate(AWSEC2InstTypes):
    metric_info['aws_ec2_running_ondemand_instances_%s' % inst_type] = {
        'title': _('Total running On-Demand %s Instances') % inst_type,
        'unit': 'count',
        'color': indexed_color(i, len(AWSEC2InstTypes)),
    }

for inst_fam in AWSEC2InstFamilies:
    metric_info['aws_ec2_running_ondemand_instances_%s_vcpu' % inst_fam[0]] = {
        'title': _('Total %s vCPUs') % AWSEC2InstFamilies[inst_fam],
        'unit': 'count',
        'color': '25/a',
    }

metric_info['aws_consumed_lcus'] = {
    'title': _('Consumed Load Balancer Capacity Units'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_active_connections'] = {
    'title': _('Active Connections'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_active_tls_connections'] = {
    'title': _('Active TLS Connections'),
    'unit': 'count',
    'color': '12/a',
}

metric_info['aws_new_connections'] = {
    'title': _('New Connections'),
    'unit': 'count',
    'color': '13/a',
}

metric_info['aws_new_tls_connections'] = {
    'title': _('New TLS Connections'),
    'unit': 'count',
    'color': '14/a',
}

metric_info['aws_rejected_connections'] = {
    'title': _('Rejected Connections'),
    'unit': 'count',
    'color': '15/a',
}

metric_info['aws_client_tls_errors'] = {
    'title': _('Client TLS errors'),
    'unit': 'count',
    'color': '21/a',
}

metric_info['aws_http_redirects'] = {
    'title': _('HTTP Redirects'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_http_redirect_url_limit'] = {
    'title': _('HTTP Redirects URL Limit Exceeded'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_http_fixed_response'] = {
    'title': _('HTTP Fixed Responses'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws__proc_bytes'] = {
    'title': _('Processed Bytes'),
    'unit': 'bytes',
    'color': '11/a',
}

metric_info['aws_proc_bytes_tls'] = {
    'title': _('TLS Processed Bytes'),
    'unit': 'bytes',
    'color': '12/a',
}

metric_info['aws_ipv6_proc_bytes'] = {
    'title': _('IPv6 Processed Bytes'),
    'unit': 'bytes',
    'color': '13/a',
}

metric_info['aws_ipv6_requests'] = {
    'title': _('IPv6 Requests'),
    'unit': 'count',
    'color': '15/a',
}

metric_info['aws_rule_evaluations'] = {
    'title': _('Rule Evaluations'),
    'unit': 'count',
    'color': '21/a',
}

metric_info['aws_failed_tls_client_handshake'] = {
    'title': _('Failed TLS Client Handshake'),
    'unit': 'count',
    'color': '21/a',
}

metric_info['aws_failed_tls_target_handshake'] = {
    'title': _('Failed TLS Target Handshake'),
    'unit': 'count',
    'color': '23/a',
}

metric_info['aws_tcp_client_rst'] = {
    'title': _('TCP Client Resets'),
    'unit': 'count',
    'color': '31/a',
}

metric_info['aws_tcp_elb_rst'] = {
    'title': _('TCP ELB Resets'),
    'unit': 'count',
    'color': '33/a',
}

metric_info['aws_tcp_target_rst'] = {
    'title': _('TCP Target Resets'),
    'unit': 'count',
    'color': '35/a',
}

metric_info['get_requests'] = {
    'title': _('GET Requests'),
    'unit': '1/s',
    'color': '11/a',
}

metric_info['put_requests'] = {
    'title': _('PUT Requests'),
    'unit': '1/s',
    'color': '13/a',
}

metric_info['delete_requests'] = {
    'title': _('DELETE Requests'),
    'unit': '1/s',
    'color': '15/a',
}

metric_info['head_requests'] = {
    'title': _('HEAD Requests'),
    'unit': '1/s',
    'color': '21/a',
}

metric_info['post_requests'] = {
    'title': _('POST Requests'),
    'unit': '1/s',
    'color': '23/a',
}

metric_info['select_requests'] = {
    'title': _('SELECT Requests'),
    'unit': '1/s',
    'color': '25/a',
}

metric_info['list_requests'] = {
    'title': _('LIST Requests'),
    'unit': '1/s',
    'color': '31/a',
}

metric_info['aws_s3_downloads'] = {
    'title': _('Download'),
    'unit': 'bytes',
    'color': '21/a',
}

metric_info['aws_s3_uploads'] = {
    'title': _('Upload'),
    'unit': 'bytes',
    'color': '31/a',
}

metric_info['aws_s3_select_object_scanned'] = {
    'title': _('SELECT Object Scanned'),
    'unit': 'bytes',
    'color': '31/a',
}

metric_info['aws_s3_select_object_returned'] = {
    'title': _('SELECT Object Returned'),
    'unit': 'bytes',
    'color': '41/a',
}

metric_info['aws_s3_buckets'] = {
    'title': _('Buckets'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_elb_load_balancers'] = {
    'title': _('Load balancers'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_elb_load_balancer_listeners'] = {
    'title': _('Load balancer listeners'),
    'unit': 'count',
    'color': '12/a',
}

metric_info['aws_elb_load_balancer_registered_instances'] = {
    'title': _('Load balancer registered instances'),
    'unit': 'count',
    'color': '13/a',
}

metric_info['aws_rds_db_clusters'] = {
    'title': _('DB clusters'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_rds_db_cluster_parameter_groups'] = {
    'title': _('DB cluster parameter groups'),
    'unit': 'count',
    'color': '12/a',
}

metric_info['aws_rds_db_instances'] = {
    'title': _('DB instances'),
    'unit': 'count',
    'color': '13/a',
}

metric_info['aws_rds_event_subscriptions'] = {
    'title': _('Event subscriptions'),
    'unit': 'count',
    'color': '14/a',
}

metric_info['aws_rds_manual_snapshots'] = {
    'title': _('Manual snapshots'),
    'unit': 'count',
    'color': '15/a',
}

metric_info['aws_rds_option_groups'] = {
    'title': _('Option groups'),
    'unit': 'count',
    'color': '16/a',
}

metric_info['aws_rds_db_parameter_groups'] = {
    'title': _('DB parameter groups'),
    'unit': 'count',
    'color': '21/a',
}

metric_info['aws_rds_read_replica_per_master'] = {
    'title': _('Read replica per master'),
    'unit': 'count',
    'color': '22/a',
}

metric_info['aws_rds_reserved_db_instances'] = {
    'title': _('Reserved DB instances'),
    'unit': 'count',
    'color': '23/a',
}

metric_info['aws_rds_db_security_groups'] = {
    'title': _('DB security groups'),
    'unit': 'count',
    'color': '24/a',
}

metric_info['aws_rds_db_subnet_groups'] = {
    'title': _('DB subnet groups'),
    'unit': 'count',
    'color': '25/a',
}

metric_info['aws_rds_subnet_per_db_subnet_groups'] = {
    'title': _('Subnet per DB subnet groups'),
    'unit': 'count',
    'color': '26/a',
}

metric_info['aws_rds_allocated_storage'] = {
    'title': _('Allocated storage'),
    'unit': 'bytes',
    'color': '31/a',
}

metric_info['aws_rds_auths_per_db_security_groups'] = {
    'title': _('Authorizations per DB security group'),
    'unit': 'count',
    'color': '32/a',
}

metric_info['aws_rds_db_cluster_roles'] = {
    'title': _('DB cluster roles'),
    'unit': 'count',
    'color': '33/a',
}

metric_info['aws_ebs_block_store_snapshots'] = {
    'title': _('Block store snapshots'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_ebs_block_store_space_standard'] = {
    'title': _('Magnetic volumes space'),
    'unit': 'bytes',
    'color': '12/a',
}

metric_info['aws_ebs_block_store_space_io1'] = {
    'title': _('Provisioned IOPS SSD space'),
    'unit': 'bytes',
    'color': '13/a',
}

metric_info['aws_ebs_block_store_iops_io1'] = {
    'title': _('Provisioned IOPS SSD IO operations per second'),
    'unit': '1/s',
    'color': '14/a',
}

metric_info['aws_ebs_block_store_space_gp2'] = {
    'title': _('General Purpose SSD space'),
    'unit': 'bytes',
    'color': '15/a',
}

metric_info['aws_ebs_block_store_space_sc1'] = {
    'title': _('Cold HDD space'),
    'unit': 'bytes',
    'color': '16/a',
}

metric_info['aws_ebs_block_store_space_st1'] = {
    'title': _('Throughput Optimized HDD space'),
    'unit': 'bytes',
    'color': '21/a',
}

metric_info['aws_elbv2_application_load_balancers'] = {
    'title': _('Application Load balancers'),
    'unit': 'count',
    'color': '11/a',
}

metric_info['aws_elbv2_application_load_balancer_rules'] = {
    'title': _('Application Load Balancer Rules'),
    'unit': 'count',
    'color': '13/a',
}

metric_info['aws_elbv2_application_load_balancer_listeners'] = {
    'title': _('Application Load Balancer Listeners'),
    'unit': 'count',
    'color': '15/a',
}

metric_info['aws_elbv2_application_load_balancer_target_groups'] = {
    'title': _('Application Load Balancer Target Groups'),
    'unit': 'count',
    'color': '21/a',
}

metric_info['aws_elbv2_application_load_balancer_certificates'] = {
    'title': _('Application Load balancer Certificates'),
    'unit': 'count',
    'color': '23/a',
}

metric_info['aws_elbv2_network_load_balancers'] = {
    'title': _('Network Load balancers'),
    'unit': 'count',
    'color': '25/a',
}

metric_info['aws_elbv2_network_load_balancer_listeners'] = {
    'title': _('Network Load Balancer Listeners'),
    'unit': 'count',
    'color': '31/a',
}

metric_info['aws_elbv2_network_load_balancer_target_groups'] = {
    'title': _('Network Load Balancer Target Groups'),
    'unit': 'count',
    'color': '33/a',
}

metric_info['aws_elbv2_load_balancer_target_groups'] = {
    'title': _('Load balancers Target Groups'),
    'unit': 'count',
    'color': '35/a',
}

metric_info['service_costs_eur'] = {
    'title': _('Service Costs per Day'),
    'unit': 'EUR',
    'color': '35/a',
}

metric_info["elapsed_time"] = {
    "title": _("Elapsed time"),
    "unit": "s",
    "color": "11/a",
}

metric_info["available_file_descriptors"] = {
    "title": _("Number of available file descriptors"),
    "unit": "count",
    "color": "21/a",
}

metric_info["app"] = {
    "title": _("Available physical processors in shared pool"),
    "unit": "count",
    "color": "11/a",
}

metric_info["entc"] = {
    "title": _("Entitled capacity consumed"),
    "unit": "%",
    "color": "12/a",
}

metric_info["lbusy"] = {
    "title": _("Logical processor(s) utilization"),
    "unit": "%",
    "color": "13/a",
}

metric_info["nsp"] = {
    "title": _("Average processor speed"),
    "unit": "%",
    "color": "14/a",
}

metric_info["phint"] = {
    "title": _("Phantom interruptions received"),
    "unit": "count",
    "color": "15/a",
}

metric_info["physc"] = {
    "title": _("Physical processors consumed"),
    "unit": "count",
    "color": "16/a",
}

metric_info["utcyc"] = {
    "title": _("Unaccounted turbo cycles"),
    "unit": "%",
    "color": "21/a",
}

metric_info["vcsw"] = {
    "title": _("Virtual context switches"),
    "unit": "%",
    "color": "22/a",
}

metric_info["job_total"] = {
    "title": _("Total number of jobs"),
    "unit": "count",
    "color": "26/a",
}

metric_info["failed_jobs"] = {
    "title": _("Total number of failed jobs"),
    "unit": "count",
    "color": "11/a",
}

metric_info["zombie_jobs"] = {
    "title": _("Total number of zombie jobs"),
    "unit": "count",
    "color": "16/a",
}

metric_info["splunk_slave_usage_bytes"] = {
    "title": _("Slave usage bytes across all pools"),
    "unit": "bytes",
    "color": "11/a",
}

metric_info["fired_alerts"] = {
    "title": _("Number of fired alerts"),
    "unit": "count",
    "color": "22/a",
}

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

metric_info["cpu_percent"] = {
    "title": _("CPU used"),
    "unit": "%",
    "color": "16/a",
}

metric_info["cpu_total_in_millis"] = {
    "title": _("CPU total in ms"),
    "unit": "1/s",
    "color": "26/a",
}

metric_info["mem_total_virtual_in_bytes"] = {
    "title": _("Total virtual memory"),
    "unit": "bytes",
    "color": "53/a",
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

metric_info["jenkins_job_score"] = {
    "title": _("Job score"),
    "unit": "%",
    "color": "11/a",
}

metric_info["jenkins_time_since"] = {
    "title": _("Time since last successful build"),
    "unit": "s",
    "color": "21/a",
}

metric_info["jenkins_build_duration"] = {
    "title": _("Build duration"),
    "unit": "s",
    "color": "31/a",
}

metric_info["jenkins_num_executors"] = {
    "title": _("Total number of executors"),
    "unit": "count",
    "color": "25/a",
}

metric_info["jenkins_busy_executors"] = {
    "title": _("Number of busy executors"),
    "unit": "count",
    "color": "11/b",
}

metric_info["jenkins_idle_executors"] = {
    "title": _("Number of idle executors"),
    "unit": "count",
    "color": "23/a",
}

metric_info["jenkins_clock"] = {
    "title": _("Clock difference"),
    "unit": "s",
    "color": "25/a",
}

metric_info["jenkins_temp"] = {
    "title": _("Available temp space"),
    "unit": "bytes",
    "color": "53/a",
}

metric_info["jenkins_stuck_tasks"] = {
    "title": _("Number of stuck tasks"),
    "unit": "count",
    "color": "11/a",
}

metric_info["jenkins_blocked_tasks"] = {
    "title": _("Number of blocked tasks"),
    "unit": "count",
    "color": "31/a",
}

metric_info["jenkins_pending_tasks"] = {
    "title": _("Number of pending tasks"),
    "unit": "count",
    "color": "51/a",
}

metric_info["msgs_avg"] = {
    "title": _("Average number of messages"),
    "unit": "count",
    "color": "23/a",
}

metric_info["index_count"] = {
    "title": _("Indices"),
    "unit": "count",
    "color": "23/a",
}

metric_info["store_size"] = {
    "title": _("Store size"),
    "unit": "bytes",
    "color": "32/a",
}

metric_info["id_cache_size"] = {
    "title": _("ID cache size"),
    "unit": "bytes",
    "color": "25/a",
}

metric_info["field_data_size"] = {
    "title": _("Field data size"),
    "unit": "bytes",
    "color": "16/a",
}

metric_info["avg_doc_size"] = {
    "title": _("Average document size"),
    "unit": "bytes",
    "color": "25/b",
}

metric_info["items_active"] = {
    "title": _("Active items"),
    "unit": "count",
    "color": "23/a",
}

metric_info["items_non_res"] = {
    "title": _("Non-resident items"),
    "unit": "count",
    "color": "23/a",
}

metric_info["items_count"] = {
    "title": _("Items"),
    "unit": "count",
    "color": "23/a",
}

metric_info["num_collections"] = {
    "title": _("Collections"),
    "unit": "count",
    "color": "11/a",
}

metric_info["num_objects"] = {
    "title": _("Objects"),
    "unit": "count",
    "color": "14/a",
}

metric_info["num_extents"] = {
    "title": _("Extents"),
    "unit": "count",
    "color": "16/a",
}

metric_info["num_input"] = {
    "title": _("Inputs"),
    "unit": "count",
    "color": "11/a",
}

metric_info["num_output"] = {
    "title": _("Outputs"),
    "unit": "count",
    "color": "14/a",
}

metric_info["num_stream_rule"] = {
    "title": _("Stream rules"),
    "unit": "count",
    "color": "16/a",
}

metric_info["num_extractor"] = {
    "title": _("Extractors"),
    "unit": "count",
    "color": "21/a",
}

metric_info["num_user"] = {
    "title": _("User"),
    "unit": "count",
    "color": "23/a",
}

for nimble_op_ty in ["read", "write"]:
    for nimble_key, nimble_title, nimble_color in [
        ("total", "Total", "11/a"),
        ("0.1", "0-0.1 ms", "12/a"),
        ("0.2", "0.1-0.2 ms", "13/a"),
        ("0.5", "0.2-0.5 ms", "14/a"),
        ("1", "0.5-1.0 ms", "15/a"),
        ("2", "1-2 ms", "16/a"),
        ("5", "2-5 ms", "21/a"),
        ("10", "5-10 ms", "22/a"),
        ("20", "10-20 ms", "23/a"),
        ("50", "20-50 ms", "24/a"),
        ("100", "50-100 ms", "25/a"),
        ("200", "100-200 ms", "26/a"),
        ("500", "200-500 ms", "31/a"),
        ("1000", "500+ ms", "32/a"),
    ]:
        metric_info["nimble_%s_latency_%s" % (nimble_op_ty, nimble_key.replace(".", ""))] = {
            "title": _("%s latency %s" % (nimble_op_ty.title(), nimble_title)),
            "unit": "s",
            "color": nimble_color,
        }

# DRBD metrics
metric_info['activity_log_updates'] = {
    "title": _("Activity log updates"),
    "unit": "count",
    "color": "31/a",
}

metric_info['bit_map_updates'] = {
    "title": _("Bit map updates"),
    "unit": "count",
    "color": "32/a",
}

metric_info['local_count_requests'] = {
    "title": _("Local count requests"),
    "unit": "count",
    "color": "24/b",
}

metric_info['pending_requests'] = {
    "title": _("Pending requests"),
    "unit": "count",
    "color": "16/a",
}

metric_info['unacknowledged_requests'] = {
    "title": _("Unacknowledged requests"),
    "unit": "count",
    "color": "16/b",
}

metric_info['application_pending_requests'] = {
    "title": _("Application pending requests"),
    "unit": "count",
    "color": "23/a",
}

metric_info['epoch_objects'] = {
    "title": _("Epoch objects"),
    "unit": "count",
    "color": "42/a",
}

metric_info['graylog_input'] = {
    "title": _("Input traffic"),
    "unit": "bytes",
    "color": "16/b",
}

metric_info['graylog_output'] = {
    "title": _("Output traffic"),
    "unit": "bytes",
    "color": "23/a",
}

metric_info['graylog_decoded'] = {
    "title": _("Decoded traffic"),
    "unit": "bytes",
    "color": "42/a",
}

metric_info["collectors_running"] = {
    "title": _("Running collectors"),
    "unit": "count",
    "color": "26/a",
}
metric_info["collectors_stopped"] = {
    "title": _("Stopped collectors"),
    "unit": "count",
    "color": "21/a",
}
metric_info["collectors_failing"] = {
    "title": _("Failing collectors"),
    "unit": "count",
    "color": "12/a",
}

metric_info["num_streams"] = {
    "title": _("Streams"),
    "unit": "count",
    "color": "11/a",
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

metric_info["item_memory"] = {
    "color": "26/a",
    "title": _("Item memory"),
    "unit": "bytes",
}

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

metric_info["resident_items_ratio"] = {
    "title": _("Resident items ratio"),
    "unit": "%",
    "color": "23/a",
}

metric_info["fetched_items"] = {
    "title": _("Number of fetched items"),
    "unit": "count",
    "color": "23/b",
}

metric_info["disk_fill_rate"] = {
    "title": _("Disk fill rate"),
    "unit": "1/s",
    "color": "31/a",
}

metric_info["disk_drain_rate"] = {
    "title": _("Disk drain rate"),
    "unit": "1/s",
    "color": "31/b",
}

# In order to use the "bytes" unit we would have to change the output of the check, (i.e. divide by
# 1024) which means an invalidation of historic values.
metric_info['kb_out_of_sync'] = {
    "title": _("KiB out of sync"),  # according to documentation
    "unit": "count",
    "color": "14/a",
}

metric_info['jira_count'] = {
    "title": _("Number of issues"),
    "unit": "count",
    "color": "14/a",
}

metric_info['jira_sum'] = {
    "title": _("Result of summed up values"),
    "unit": "count",
    "color": "14/a",
}

metric_info['jira_avg'] = {
    "title": _("Average value"),
    "unit": "count",
    "color": "14/a",
}

metric_info['jira_diff'] = {
    "title": _("Difference"),
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

metric_info['channels'] = {
    "title": _("Channels"),
    "unit": "count",
    "color": "11/a",
}

metric_info['consumers'] = {
    "title": _("Consumers"),
    "unit": "count",
    "color": "21/a",
}

metric_info['exchanges'] = {
    "title": _("Exchanges"),
    "unit": "count",
    "color": "26/a",
}

metric_info['queues'] = {
    "title": _("Queues"),
    "unit": "count",
    "color": "31/a",
}

metric_info['messages_rate'] = {
    "title": _("Message Rate"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info['messages_ready'] = {
    "title": _("Ready messages"),
    "unit": "count",
    "color": "11/a",
}

metric_info['messages_unacknowledged'] = {
    "title": _("Unacknowledged messages"),
    "unit": "count",
    "color": "14/a",
}

metric_info['messages_publish'] = {
    "title": _("Published messages"),
    "unit": "count",
    "color": "31/a",
}

metric_info['messages_publish_rate'] = {
    "title": _("Published message rate"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info['messages_deliver'] = {
    "title": _("Delivered messages"),
    "unit": "count",
    "color": "26/a",
}

metric_info['messages_deliver_rate'] = {
    "title": _("Delivered message rate"),
    "unit": "1/s",
    "color": "53/a",
}

metric_info['gc_runs'] = {
    "title": _("GC runs"),
    "unit": "count",
    "color": "31/a",
}

metric_info['gc_runs_rate'] = {
    "title": _("GC runs rate"),
    "unit": "1/s",
    "color": "53/a",
}

metric_info['runtime_run_queue'] = {
    "title": _("Runtime run queue"),
    "unit": "count",
    "color": "21/a",
}

metric_info['gc_bytes'] = {
    "title": _("Bytes reclaimed by GC"),
    "unit": "bytes",
    "color": "32/a",
}

metric_info['gc_bytes_rate'] = {
    "title": _("Bytes reclaimed by GC rate"),
    "unit": "bytes/s",
    "color": "42/a",
}

metric_info['log_file_utilization'] = {
    "title": _("Percentage of log file used"),
    "unit": "%",
    "color": "42/a",
}

metric_info['clients_connected'] = {
    "title": _("Connected clients"),
    "unit": "count",
    "color": "11/a",
}

metric_info['clients_output'] = {
    "title": _("Longest output list"),
    "unit": "count",
    "color": "14/a",
}

metric_info['clients_input'] = {
    "title": _("Biggest input buffer"),
    "unit": "count",
    "color": "21/a",
}

metric_info['clients_blocked'] = {
    "title": _("Clients pending on a blocking call"),
    "unit": "count",
    "color": "32/a",
}

metric_info['changes_sld'] = {
    "title": _("Changes since last dump"),
    "unit": "count",
    "color": "11/a",
}
#.
#   .--Checks--------------------------------------------------------------.
#   |                    ____ _               _                            |
#   |                   / ___| |__   ___  ___| | _____                     |
#   |                  | |   | '_ \ / _ \/ __| |/ / __|                    |
#   |                  | |___| | | |  __/ (__|   <\__ \                    |
#   |                   \____|_| |_|\___|\___|_|\_\___/                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  How various checks' performance data translate into the known       |
#   |  metrics                                                             |
#   '----------------------------------------------------------------------'

check_metrics["check_mk_active-icmp"] = {
    "rta": {
        "scale": m
    },
    "rtmax": {
        "scale": m
    },
    "rtmin": {
        "scale": m
    },
}

# This metric is not for an official Check_MK check
# It may be provided by an check_icmp check configured as mrpe
check_metrics["check_icmp"] = {
    "~.*rta": {
        "scale": m
    },
    "~.*rtmax": {
        "scale": m
    },
    "~.*rtmin": {
        "scale": m
    },
}

check_metrics["check_tcp"] = {
    "time": {
        "name": "response_time"
    },
}

check_metrics["check-mk-host-ping"] = {
    "rta": {
        "scale": m
    },
    "rtmax": {
        "scale": m
    },
    "rtmin": {
        "scale": m
    },
}

check_metrics["check-mk-host-service"] = {
    "rta": {
        "scale": m
    },
    "rtmax": {
        "scale": m
    },
    "rtmin": {
        "scale": m
    },
}

check_metrics["check-mk-ping"] = {
    "rta": {
        "scale": m
    },
    "rtmax": {
        "scale": m
    },
    "rtmin": {
        "scale": m
    },
}

check_metrics["check-mk-host-ping-cluster"] = {
    "~.*rta": {
        "name": "rta",
        "scale": m
    },
    "~.*pl": {
        "name": "pl",
        "scale": m
    },
    "~.*rtmax": {
        "name": "rtmax",
        "scale": m
    },
    "~.*rtmin": {
        "name": "rtmin",
        "scale": m
    },
}

check_metrics["check_mk_active-mail_loop"] = {
    "duration": {
        "name": "mails_received_time"
    },
}

check_metrics["check_mk_active-http"] = {
    "time": {
        "name": "response_time"
    },
    "size": {
        "name": "response_size"
    },
}

check_metrics["check_mk_active-tcp"] = {
    "time": {
        "name": "response_time"
    },
}

check_metrics["check_mk_active-ldap"] = {
    "time": {
        "name": "response_time"
    },
}

check_metrics["check-mk-host-tcp"] = {
    "time": {
        "name": "response_time"
    },
}

for check in [
        'winperf_processor.util', 'docker_container_cpu', 'hr_cpu', 'bintec_cpu',
        'esx_vsphere_hostsystem'
]:
    check_metrics["check_mk-%s" % check] = {
        "avg": {
            "name": "util_average"
        },
    }

check_metrics["check_mk-winperf_processor.util"].update({"util": {"name": "util_numcpu_as_max"}})
check_metrics["check_mk-netapp_api_cpu"] = {"util": {"name": "util_numcpu_as_max"}}
check_metrics["check_mk-netapp_api_cpu.utilization"] = {"util": {"name": "util_numcpu_as_max"}}

check_metrics["check_mk-citrix_serverload"] = {
    "perf": {
        "name": "citrix_load",
        "scale": 0.01
    },
}

check_metrics["check_mk-genau_fan"] = {
    "rpm": {
        "name": "fan"
    },
}

check_metrics["check_mk-openbsd_sensors"] = {
    "rpm": {
        "name": "fan"
    },
}

check_metrics["check_mk-postfix_mailq"] = {
    "length": {
        "name": "mail_queue_deferred_length"
    },
    "size": {
        "name": "mail_queue_deferred_size"
    },
    "~mail_queue_.*_size": {
        "name": "mail_queue_active_size"
    },
    "~mail_queue_.*_length": {
        "name": "mail_queue_active_length"
    },
}

check_metrics["check_mk-jolokia_metrics.gc"] = {
    "CollectionCount": {
        "name": "jvm_garbage_collection_count",
        "scale": 1 / 60.0,
    },
    "CollectionTime": {
        "name": "jvm_garbage_collection_time",
        "scale": 1 / 600.0,  # ms/min -> %
    },
}

check_metrics["check_mk-rmon_stats"] = {
    "bcast": {
        "name": "broadcast_packets"
    },
    "mcast": {
        "name": "multicast_packets"
    },
    "0-63b": {
        "name": "rmon_packets_63"
    },
    "64-127b": {
        "name": "rmon_packets_127"
    },
    "128-255b": {
        "name": "rmon_packets_255"
    },
    "256-511b": {
        "name": "rmon_packets_511"
    },
    "512-1023b": {
        "name": "rmon_packets_1023"
    },
    "1024-1518b": {
        "name": "rmon_packets_1518"
    },
}

check_metrics["check_mk-cpu.loads"] = {
    "load5": {
        "auto_graph": False
    },
}

check_metrics["check_mk-ucd_cpu_load"] = {
    "load5": {
        "auto_graph": False
    },
}

check_metrics["check_mk-statgrab_load"] = {
    "load5": {
        "auto_graph": False
    },
}

check_metrics["check_mk-hpux_cpu"] = {
    "wait": {
        "name": "io_wait"
    },
}

check_metrics["check_mk-hitachi_hnas_cpu"] = {
    "cpu_util": {
        "name": "util"
    },
}

check_metrics["check_mk-hitachi_hnas_cifs"] = {
    "users": {
        "name": "cifs_share_users"
    },
}

check_metrics["check_mk-hitachi_hnas_fan"] = {
    "fanspeed": {
        "name": "fan"
    },
}

check_metrics["check_mk-statgrab_disk"] = {
    "read": {
        "name": "disk_read_throughput"
    },
    "write": {
        "name": "disk_write_throughput"
    }
}

check_metrics["check_mk-ibm_svc_systemstats.diskio"] = {
    "read": {
        "name": "disk_read_throughput"
    },
    "write": {
        "name": "disk_write_throughput"
    }
}

check_metrics["check_mk-ibm_svc_nodestats.diskio"] = {
    "read": {
        "name": "disk_read_throughput"
    },
    "write": {
        "name": "disk_write_throughput"
    }
}

memory_simple_translation = {
    "memory_used": {
        "name": "mem_used",
        "deprecated": True,
    },
}

check_metrics["check_mk-hp_procurve_mem"] = memory_simple_translation
check_metrics["check_mk-datapower_mem"] = memory_simple_translation
check_metrics["check_mk-ucd_mem"] = memory_simple_translation
check_metrics["check_mk-netscaler_mem"] = memory_simple_translation

ram_used_swap_translation = {
    "ramused": {
        "name": "mem_used",
        "scale": MB,
        "deprecated": True,
    },
    "mem_used_percent": {
        "auto_graph": False,
    },
    "swapused": {
        "name": "swap_used",
        "scale": MB,
        "deprecated": True,
    },
    "memused": {
        "name": "mem_lnx_total_used",
        "auto_graph": False,
        "scale": MB,
        "deprecated": True,
    },
    "mem_lnx_total_used": {
        "auto_graph": False,
    },
    "memusedavg": {
        "name": "memory_avg",
        "scale": MB
    },
    "shared": {
        "name": "mem_lnx_shmem",
        "deprecated": True,
        "scale": MB
    },
    "pagetables": {
        "name": "mem_lnx_page_tables",
        "deprecated": True,
        "scale": MB
    },
    "mapped": {
        "name": "mem_lnx_mapped",
        "deprecated": True,
        "scale": MB
    },
    "committed_as": {
        "name": "mem_lnx_committed_as",
        "deprecated": True,
        "scale": MB
    },
}

check_metrics["check_mk-statgrab_mem"] = ram_used_swap_translation
check_metrics["check_mk-hr_mem"] = ram_used_swap_translation
check_metrics["check_mk-solaris_mem"] = ram_used_swap_translation
check_metrics["check_mk-docker_container_mem"] = ram_used_swap_translation
check_metrics["check_mk-emc_ecs_mem"] = ram_used_swap_translation
check_metrics["check_mk-aix_memory"] = ram_used_swap_translation
check_metrics["check_mk-mem.used"] = ram_used_swap_translation

check_metrics["check_mk-esx_vsphere_vm.mem_usage"] = {
    "host": {
        "name": "mem_esx_host"
    },
    "guest": {
        "name": "mem_esx_guest"
    },
    "ballooned": {
        "name": "mem_esx_ballooned"
    },
    "shared": {
        "name": "mem_esx_shared"
    },
    "private": {
        "name": "mem_esx_private"
    },
}

check_metrics["check_mk-ibm_svc_nodestats.disk_latency"] = {
    "read_latency": {
        "scale": m
    },
    "write_latency": {
        "scale": m
    },
}

check_metrics["check_mk-ibm_svc_systemstats.disk_latency"] = {
    "read_latency": {
        "scale": m
    },
    "write_latency": {
        "scale": m
    },
}

check_metrics["check_mk-netapp_api_disk.summary"] = {
    "total_disk_capacity": {
        "name": "disk_capacity"
    },
    "total_disks": {
        "name": "disks"
    },
}

check_metrics["check_mk-emc_isilon_iops"] = {
    "iops": {
        "name": "disk_ios"
    },
}

check_metrics["check_mk-vms_system.ios"] = {
    "direct": {
        "name": "direct_io"
    },
    "buffered": {
        "name": "buffered_io"
    }
}

check_metrics["check_mk-kernel"] = {
    "ctxt": {
        "name": "context_switches"
    },
    "pgmajfault": {
        "name": "major_page_faults"
    },
    "processes": {
        "name": "process_creations"
    },
}

check_metrics["check_mk-oracle_jobs"] = {
    "duration": {
        "name": "job_duration"
    },
}

check_metrics["check_mk-oracle_recovery_area"] = {
    "used": {
        "name": "database_size",
        "scale": MB
    },
    "reclaimable": {
        "name": "database_reclaimable",
        "scale": MB
    },
}

check_metrics["check_mk-vms_system.procs"] = {
    "procs": {
        "name": "processes"
    },
}

check_metrics["check_mk-jolokia_metrics.tp"] = {
    "currentThreadCount": {
        "name": "threads_idle"
    },
    "currentThreadsBusy": {
        "name": "threads_busy"
    },
}

check_metrics["check_mk-mem.win"] = {
    "memory": {
        "name": "mem_used",
        "scale": MB,
        "deprecated": True
    },
    "pagefile": {
        "name": "pagefile_used",
        "scale": MB
    },
    "memory_avg": {
        "scale": MB
    },
    "pagefile_avg": {
        "scale": MB
    },
    "mem_total": {
        "auto_graph": False,
        "scale": MB
    },
    "pagefile_total": {
        "auto_graph": False,
        "scale": MB
    },
}

check_metrics["check_mk-brocade_mlx.module_mem"] = {
    "memused": {
        "name": "mem_used",
        "deprecated": True,
    },
}

check_metrics["check_mk-jolokia_metrics.mem"] = {
    "heap": {
        "name": "mem_heap",
        "scale": MB
    },
    "nonheap": {
        "name": "mem_nonheap",
        "scale": MB
    }
}

check_metrics["check_mk-jolokia_metrics.threads"] = {
    "ThreadRate": {
        "name": "threads_rate"
    },
    "ThreadCount": {
        "name": "threads"
    },
    "DeamonThreadCount": {
        "name": "threads_daemon"
    },
    "PeakThreadCount": {
        "name": "threads_max"
    },
    "TotalStartedThreadCount": {
        "name": "threads_total"
    },
}

check_metrics["check_mk-mem.linux"] = {
    "cached": {
        "name": "mem_lnx_cached",
    },
    "buffers": {
        "name": "mem_lnx_buffers",
    },
    "slab": {
        "name": "mem_lnx_slab",
    },
    "active_anon": {
        "name": "mem_lnx_active_anon",
    },
    "active_file": {
        "name": "mem_lnx_active_file",
    },
    "inactive_anon": {
        "name": "mem_lnx_inactive_anon",
    },
    "inactive_file": {
        "name": "mem_lnx_inactive_file",
    },
    "dirty": {
        "name": "mem_lnx_dirty",
    },
    "writeback": {
        "name": "mem_lnx_writeback",
    },
    "nfs_unstable": {
        "name": "mem_lnx_nfs_unstable",
    },
    "bounce": {
        "name": "mem_lnx_bounce",
    },
    "writeback_tmp": {
        "name": "mem_lnx_writeback_tmp",
    },
    "total_total": {
        "name": "mem_lnx_total_total",
    },
    "committed_as": {
        "name": "mem_lnx_committed_as",
    },
    "commit_limit": {
        "name": "mem_lnx_commit_limit",
    },
    "shmem": {
        "name": "mem_lnx_shmem",
    },
    "kernel_stack": {
        "name": "mem_lnx_kernel_stack",
    },
    "page_tables": {
        "name": "mem_lnx_page_tables",
    },
    "mlocked": {
        "name": "mem_lnx_mlocked",
    },
    "huge_pages_total": {
        "name": "mem_lnx_huge_pages_total",
    },
    "huge_pages_free": {
        "name": "mem_lnx_huge_pages_free",
    },
    "huge_pages_rsvd": {
        "name": "mem_lnx_huge_pages_rsvd",
    },
    "huge_pages_surp": {
        "name": "mem_lnx_huge_pages_surp",
    },
    "vmalloc_total": {
        "name": "mem_lnx_vmalloc_total",
    },
    "vmalloc_used": {
        "name": "mem_lnx_vmalloc_used",
    },
    "vmalloc_chunk": {
        "name": "mem_lnx_vmalloc_chunk",
    },
    "hardware_corrupted": {
        "name": "mem_lnx_hardware_corrupted",
    },

    # Several computed values should not be graphed because they
    # are already contained in the other graphs. Or because they
    # are bizarre
    "caches": {
        "name": "caches",
        "auto_graph": False
    },
    "swap_free": {
        "name": "swap_free",
        "auto_graph": False
    },
    "mem_free": {
        "name": "mem_free",
        "auto_graph": False
    },
    "sreclaimable": {
        "name": "mem_lnx_sreclaimable",
        "auto_graph": False
    },
    "pending": {
        "name": "mem_lnx_pending",
        "auto_graph": False
    },
    "sunreclaim": {
        "name": "mem_lnx_sunreclaim",
        "auto_graph": False
    },
    "anon_huge_pages": {
        "name": "mem_lnx_anon_huge_pages",
        "auto_graph": False
    },
    "anon_pages": {
        "name": "mem_lnx_anon_pages",
        "auto_graph": False
    },
    "mapped": {
        "name": "mem_lnx_mapped",
        "auto_graph": False
    },
    "active": {
        "name": "mem_lnx_active",
        "auto_graph": False
    },
    "inactive": {
        "name": "mem_lnx_inactive",
        "auto_graph": False
    },
    "total_used": {
        "name": "mem_lnx_total_used",
        "auto_graph": False
    },
    "unevictable": {
        "name": "mem_lnx_unevictable",
        "auto_graph": False
    },
    "cma_free": {
        "auto_graph": False
    },
    "cma_total": {
        "auto_graph": False
    },
}

check_metrics["check_mk-mem.vmalloc"] = {
    "used": {
        "name": "mem_lnx_vmalloc_used"
    },
    "chunk": {
        "name": "mem_lnx_vmalloc_chunk"
    }
}

tcp_conn_stats_translation = {
    "SYN_SENT": {
        "name": "tcp_syn_sent"
    },
    "SYN_RECV": {
        "name": "tcp_syn_recv"
    },
    "ESTABLISHED": {
        "name": "tcp_established"
    },
    "LISTEN": {
        "name": "tcp_listen"
    },
    "TIME_WAIT": {
        "name": "tcp_time_wait"
    },
    "LAST_ACK": {
        "name": "tcp_last_ack"
    },
    "CLOSE_WAIT": {
        "name": "tcp_close_wait"
    },
    "CLOSED": {
        "name": "tcp_closed"
    },
    "CLOSING": {
        "name": "tcp_closing"
    },
    "FIN_WAIT1": {
        "name": "tcp_fin_wait1"
    },
    "FIN_WAIT2": {
        "name": "tcp_fin_wait2"
    },
    "BOUND": {
        "name": "tcp_bound"
    },
    "IDLE": {
        "name": "tcp_idle"
    },
}
check_metrics["check_mk-tcp_conn_stats"] = tcp_conn_stats_translation
check_metrics["check_mk-datapower_tcp"] = tcp_conn_stats_translation

check_metrics["check_mk_active-disk_smb"] = {
    "~.*": {
        "name": "fs_used"
    },
}

df_basic_perfvarnames = [
    "inodes_used", "fs_size", "growth", "trend", "reserved", "fs_free", "fs_provisioning",
    "uncommitted", "overprovisioned"
]
df_translation = {
    "~(?!%s).*$" % "|".join(df_basic_perfvarnames): {
        "name": "fs_used",
        "scale": MB,
        "deprecated": True
    },
    "fs_used": {
        "scale": MB
    },
    "fs_used_percent": {
        "auto_graph": False,
    },
    "fs_size": {
        "scale": MB
    },
    "reserved": {
        "scale": MB
    },
    "fs_free": {
        "scale": MB
    },
    "growth": {
        "name": "fs_growth",
        "scale": MB / 86400.0
    },
    "trend": {
        "name": "fs_trend",
        "scale": MB / 86400.0
    },
    "trend_hoursleft": {
        "scale": 3600,
    },
    "uncommitted": {
        "scale": MB,
    },
    "overprovisioned": {
        "scale": MB,
    },
}

check_metrics["check_mk-df"] = df_translation
check_metrics["check_mk-esx_vsphere_datastores"] = df_translation
check_metrics["check_mk-netapp_api_aggr"] = df_translation
check_metrics["check_mk-vms_df"] = df_translation
check_metrics["check_mk-vms_diskstat.df"] = df_translation
check_metrics["check_disk"] = df_translation
check_metrics["check_mk-df_netapp"] = df_translation
check_metrics["check_mk-df_netapp32"] = df_translation
check_metrics["check_mk-zfsget"] = df_translation
check_metrics["check_mk-hr_fs"] = df_translation
check_metrics["check_mk-oracle_asm_diskgroup"] = df_translation
check_metrics["check_mk-esx_vsphere_counters.ramdisk"] = df_translation
check_metrics["check_mk-hitachi_hnas_span"] = df_translation
check_metrics["check_mk-hitachi_hnas_volume"] = df_translation
check_metrics["check_mk-hitachi_hnas_volume.virtual"] = df_translation
check_metrics["check_mk-emcvnx_raidgroups.capacity"] = df_translation
check_metrics["check_mk-emcvnx_raidgroups.capacity_contiguous"] = df_translation
check_metrics["check_mk-ibm_svc_mdiskgrp"] = df_translation
check_metrics["check_mk-fast_lta_silent_cubes.capacity"] = df_translation
check_metrics["check_mk-fast_lta_volumes"] = df_translation
check_metrics["check_mk-libelle_business_shadow.archive_dir"] = df_translation
check_metrics["check_mk-netapp_api_volumes"] = df_translation
check_metrics["check_mk-netapp_api_luns"] = df_translation
check_metrics["check_mk-netapp_api_qtree_quota"] = df_translation
check_metrics["check_mk-emc_datadomain_fs"] = df_translation
check_metrics["check_mk-emc_isilon_quota"] = df_translation
check_metrics["check_mk-emc_isilon_ifs"] = df_translation
check_metrics["check_mk-3par_cpgs.usage"] = df_translation
check_metrics["check_mk-3par_capacity"] = df_translation
check_metrics["check_mk-3par_volumes"] = df_translation
check_metrics["check_mk-storeonce_clusterinfo.space"] = df_translation
check_metrics["check_mk-storeonce_servicesets.capacity"] = df_translation
check_metrics["check_mk-numble_volumes"] = df_translation
check_metrics["check_mk-zpool"] = df_translation
check_metrics["check_mk-vnx_quotas"] = df_translation
check_metrics["check_mk-k8s_stats.fs"] = df_translation
check_metrics["check_mk-fjdarye200_pools"] = df_translation

df_netapp_perfvarnames = list(df_basic_perfvarnames)
for protocol in ["nfs", "cifs", "san", "fcp", "iscsi", "nfsv4", "nfsv4_1"]:
    df_netapp_perfvarnames.append("%s_read_data" % protocol)
    df_netapp_perfvarnames.append("%s_write_data" % protocol)
    df_netapp_perfvarnames.append("%s_read_latency" % protocol)
    df_netapp_perfvarnames.append("%s_write_latency" % protocol)
    df_netapp_perfvarnames.append("%s_read_ops" % protocol)
    df_netapp_perfvarnames.append("%s_write_ops" % protocol)

# TODO: this special regex construct below, needs to be replaced by something managable
# The current df_translation implementation is unable to automatically detect new parameters
check_metrics["check_mk-netapp_api_volumes"] = {
    "~(?!%s).*$" % "|".join(df_netapp_perfvarnames): {
        "name": "fs_used",
        "scale": MB,
        "deprecated": True
    },
    "fs_used": {
        "scale": MB
    },
    "fs_used_percent": {
        "auto_graph": False,
    },
    "fs_size": {
        "scale": MB
    },
    "growth": {
        "name": "fs_growth",
        "scale": MB / 86400.0
    },
    "trend": {
        "name": "fs_trend",
        "scale": MB / 86400.0
    },
    "read_latency": {
        "scale": m
    },
    "write_latency": {
        "scale": m
    },
    "other_latency": {
        "scale": m
    },
    "nfs_read_latency": {
        "scale": m
    },
    "nfs_write_latency": {
        "scale": m
    },
    "nfs_other_latency": {
        "scale": m
    },
    "cifs_read_latency": {
        "scale": m
    },
    "cifs_write_latency": {
        "scale": m
    },
    "cifs_other_latency": {
        "scale": m
    },
    "san_read_latency": {
        "scale": m
    },
    "san_write_latency": {
        "scale": m
    },
    "san_other_latency": {
        "scale": m
    },
    "fcp_read_latency": {
        "scale": m
    },
    "fcp_write_latency": {
        "scale": m
    },
    "fcp_other_latency": {
        "scale": m
    },
    "iscsi_read_latency": {
        "scale": m
    },
    "iscsi_write_latency": {
        "scale": m
    },
    "iscsi_other_latency": {
        "scale": m
    },
}

disk_utilization_translation = {
    "disk_utilization": {
        "scale": 100.0
    },
}

check_metrics["check_mk-diskstat"] = disk_utilization_translation
check_metrics["check_mk-emc_vplex_director_stats"] = disk_utilization_translation
check_metrics["check_mk-emc_vplex_volumes"] = disk_utilization_translation
check_metrics["check_mk-esx_vsphere_counters.diskio"] = disk_utilization_translation
check_metrics["check_mk-hp_msa_controller.io"] = disk_utilization_translation
check_metrics["check_mk-hp_msa_disk.io"] = disk_utilization_translation
check_metrics["check_mk-hp_msa_volume.io"] = disk_utilization_translation
check_metrics["check_mk-winperf_phydisk"] = disk_utilization_translation
check_metrics["check_mk-arbor_peakflow_sp.disk_usage"] = disk_utilization_translation
check_metrics["check_mk-arbor_peakflow_tms.disk_usage"] = disk_utilization_translation
check_metrics["check_mk-arbor_pravail.disk_usage"] = disk_utilization_translation

# in=0;;;0; inucast=0;;;; innucast=0;;;; indisc=0;;;; inerr=0;0.01;0.1;; out=0;;;0; outucast=0;;;; outnucast=0;;;; outdisc=0;;;; outerr=0;0.01;0.1;; outqlen=0;;;0;
if_translation = {
    "in": {
        "name": "if_in_bps",
        "scale": 8
    },
    "out": {
        "name": "if_out_bps",
        "scale": 8
    },
    "indisc": {
        "name": "if_in_discards"
    },
    "inerr": {
        "name": "if_in_errors"
    },
    "outdisc": {
        "name": "if_out_discards"
    },
    "outerr": {
        "name": "if_out_errors"
    },
    "inucast": {
        "name": "if_in_unicast"
    },
    "innucast": {
        "name": "if_in_non_unicast"
    },
    "outucast": {
        "name": "if_out_unicast"
    },
    "outnucast": {
        "name": "if_out_non_unicast"
    },
}

check_metrics["check_mk-esx_vsphere_counters"] = if_translation
check_metrics["check_mk-esx_vsphere_counters.if"] = if_translation
check_metrics["check_mk-fritz"] = if_translation
check_metrics["check_mk-fritz.wan_if"] = if_translation
check_metrics["check_mk-hitachi_hnas_fc_if"] = if_translation
check_metrics["check_mk-if64"] = if_translation
check_metrics["check_mk-if64adm"] = if_translation
check_metrics["check_mk-hpux_if"] = if_translation
check_metrics["check_mk-if64_tplink"] = if_translation
check_metrics["check_mk-if_lancom"] = if_translation
check_metrics["check_mk-if_brocade"] = if_translation
check_metrics["check_mk-if"] = if_translation
check_metrics["check_mk-lnx_if"] = if_translation
check_metrics["check_mk-cadvisor_if"] = if_translation
check_metrics["check_mk-mcdata_fcport"] = if_translation
check_metrics["check_mk-netapp_api_if"] = if_translation
check_metrics["check_mk-statgrab_net"] = if_translation
check_metrics["check_mk-ucs_bladecenter_if"] = if_translation
check_metrics["check_mk-vms_if"] = if_translation
check_metrics["check_mk-winperf_if"] = if_translation
check_metrics["check_mk-emc_vplex_if"] = if_translation
check_metrics["check_mk-huawei_osn_if"] = if_translation
check_metrics["check_mk-if_fortigate"] = if_translation
check_metrics["check_mk-aix_if"] = if_translation
check_metrics["check_mk-k8s_stats.network"] = if_translation
check_metrics["check_mk-aws_ec2.network_io"] = if_translation
check_metrics["check_mk-aws_rds.network_io"] = if_translation

check_metrics["check_mk-brocade_fcport"] = {
    "in": {
        "name": "fc_rx_bytes",
    },
    "out": {
        "name": "fc_tx_bytes",
    },
    "rxframes": {
        "name": "fc_rx_frames",
    },
    "txframes": {
        "name": "fc_tx_frames",
    },
    "rxcrcs": {
        "name": "fc_crc_errors"
    },
    "rxencoutframes": {
        "name": "fc_encouts"
    },
    "rxencinframes": {
        "name": "fc_encins"
    },
    "c3discards": {
        "name": "fc_c3discards"
    },
    "notxcredits": {
        "name": "fc_notxcredits"
    },
}

check_metrics["check_mk-fc_port"] = {
    "in": {
        "name": "fc_rx_bytes",
    },
    "out": {
        "name": "fc_tx_bytes",
    },
    "rxobjects": {
        "name": "fc_rx_frames",
    },
    "txobjects": {
        "name": "fc_tx_frames",
    },
    "rxcrcs": {
        "name": "fc_crc_errors"
    },
    "rxencoutframes": {
        "name": "fc_encouts"
    },
    "c3discards": {
        "name": "fc_c3discards"
    },
    "notxcredits": {
        "name": "fc_notxcredits"
    },
}

check_metrics["check_mk-qlogic_fcport"] = {
    "in": {
        "name": "fc_rx_bytes",
    },
    "out": {
        "name": "fc_tx_bytes",
    },
    "rxframes": {
        "name": "fc_rx_frames",
    },
    "txframes": {
        "name": "fc_tx_frames",
    },
    "link_failures": {
        "name": "fc_link_fails"
    },
    "sync_losses": {
        "name": "fc_sync_losses"
    },
    "prim_seq_proto_errors": {
        "name": "fc_prim_seq_errors"
    },
    "invalid_tx_words": {
        "name": "fc_invalid_tx_words"
    },
    "discards": {
        "name": "fc_c2c3_discards"
    },
    "invalid_crcs": {
        "name": "fc_invalid_crcs"
    },
    "address_id_errors": {
        "name": "fc_address_id_errors"
    },
    "link_reset_ins": {
        "name": "fc_link_resets_in"
    },
    "link_reset_outs": {
        "name": "fc_link_resets_out"
    },
    "ols_ins": {
        "name": "fc_offline_seqs_in"
    },
    "ols_outs": {
        "name": "fc_offline_seqs_out"
    },
    "c2_fbsy_frames": {
        "name": "fc_c2_fbsy_frames"
    },
    "c2_frjt_frames": {
        "name": "fc_c2_frjt_frames"
    },
}

check_metrics["check_mk-mysql.innodb_io"] = {
    "read": {
        "name": "disk_read_throughput"
    },
    "write": {
        "name": "disk_write_throughput"
    }
}

check_metrics["check_mk-esx_vsphere_counters.diskio"] = {
    "read": {
        "name": "disk_read_throughput"
    },
    "write": {
        "name": "disk_write_throughput"
    },
    "ios": {
        "name": "disk_ios"
    },
    "latency": {
        "name": "disk_latency"
    },
    "disk_utilization": {
        "scale": 100.0
    },
}

check_metrics["check_mk-emcvnx_disks"] = {
    "read": {
        "name": "disk_read_throughput"
    },
    "write": {
        "name": "disk_write_throughput"
    }
}

check_metrics["check_mk-diskstat"] = {
    "read": {
        "name": "disk_read_throughput"
    },
    "write": {
        "name": "disk_write_throughput"
    },
    "disk_utilization": {
        "scale": 100.0
    },
}

check_metrics["check_mk-aix_diskiod"] = {
    "read": {
        "name": "disk_read_throughput"
    },
    "write": {
        "name": "disk_write_throughput"
    },
    "disk_utilization": {
        "scale": 100.0
    },
}

check_metrics["check_mk-ibm_svc_systemstats.iops"] = {
    "read": {
        "name": "disk_read_ios"
    },
    "write": {
        "name": "disk_write_ios"
    }
}

check_metrics["check_mk-docker_node_info.containers"] = {
    "containers": {
        "name": "docker_all_containers"
    },
    "running": {
        "name": "docker_running_containers"
    },
    "paused": {
        "name": "docker_paused_containers"
    },
    "stopped": {
        "name": "docker_stopped_containers"
    },
}

check_metrics["check_mk-docker_node_disk_usage"] = {
    "count": {
        "name": "docker_count"
    },
    "active": {
        "name": "docker_active"
    },
    "size": {
        "name": "docker_size"
    },
    "reclaimable": {
        "name": "docker_reclaimable"
    },
}

check_metrics["check_mk-dell_powerconnect_temp"] = {
    "temperature": {
        "name": "temp"
    },
}

check_metrics["check_mk-bluecoat_diskcpu"] = {
    "value": {
        "name": "generic_util"
    },
}

check_metrics["check_mk-mgmt_ipmi_sensors"] = {
    "value": {
        "name": "temp"
    },
}

check_metrics["check_mk-ipmi_sensors"] = {
    "value": {
        "name": "temp"
    },
}

check_metrics["check_mk-ipmi"] = {
    "ambient_temp": {
        "name": "temp"
    },
}

check_metrics["check_mk-wagner_titanus_topsense.airflow_deviation"] = {
    "airflow_deviation": {
        "name": "deviation_airflow"
    }
}

check_metrics["check_mk-wagner_titanus_topsense.chamber_deviation"] = {
    "chamber_deviation": {
        "name": "deviation_calibration_point"
    }
}

check_metrics["check_mk-apc_symmetra"] = {
    "OutputLoad": {
        "name": "output_load"
    },
    "batcurr": {
        "name": "battery_current"
    },
    "systemp": {
        "name": "battery_temp"
    },
    "capacity": {
        "name": "battery_capacity"
    },
    "runtime": {
        "name": "lifetime_remaining",
        "scale": 60
    },
}

check_metrics["check_mk-apc_symmetra.temp"] = {
    "systemp": {
        "name": "battery_temp"
    },
}

check_metrics["check_mk-apc_symmetra.elphase"] = {
    "OutputLoad": {
        "name": "output_load"
    },
    "batcurr": {
        "name": "battery_current"
    },
}

cpu_util_unix_translate = {
    "wait": {
        "name": "io_wait"
    },
    "guest": {
        "name": "cpu_util_guest"
    },
    "steal": {
        "name": "cpu_util_steal"
    },
}

check_metrics["check_mk-kernel.util"] = cpu_util_unix_translate
check_metrics["check_mk-statgrab_cpu"] = cpu_util_unix_translate
check_metrics["check_mk-lxc_container_cpu"] = cpu_util_unix_translate
check_metrics["check_mk-emc_ecs_cpu_util"] = cpu_util_unix_translate

check_metrics["check_mk-lparstat_aix.cpu_util"] = {
    "wait": {
        "name": "io_wait"
    },
}

check_metrics["check_mk-ucd_cpu_util"] = {
    "wait": {
        "name": "io_wait"
    },
}

check_metrics["check_mk-vms_cpu"] = {
    "wait": {
        "name": "io_wait"
    },
}

check_metrics["check_mk-vms_sys.util"] = {
    "wait": {
        "name": "io_wait"
    },
}

check_metrics["check_mk-winperf.cpuusage"] = {
    "cpuusage": {
        "name": "util"
    },
}

check_metrics["check_mk-h3c_lanswitch_cpu"] = {
    "usage": {
        "name": "util"
    },
}

check_metrics["check_mk-brocade_mlx.module_cpu"] = {
    "cpu_util1": {
        "name": "util1s"
    },
    "cpu_util5": {
        "name": "util5s"
    },
    "cpu_util60": {
        "name": "util1"
    },
    "cpu_util200": {
        "name": "util5"
    },
}

check_metrics["check_mk-dell_powerconnect_cpu"] = {
    "load": {
        "name": "util"
    },
    "loadavg 60s": {
        "name": "util1"
    },
    "loadavg 5m": {
        "name": "util5"
    },
}

check_metrics["check_mk-ibm_svc_nodestats.cache"] = {
    "write_cache_pc": {
        "name": "write_cache_usage"
    },
    "total_cache_pc": {
        "name": "total_cache_usage"
    }
}

check_metrics["check_mk-ibm_svc_systemstats.cache"] = {
    "write_cache_pc": {
        "name": "write_cache_usage"
    },
    "total_cache_pc": {
        "name": "total_cache_usage"
    }
}

mem_vsphere_hostsystem = {
    "usage": {
        "name": "mem_used",
        "deprecated": True
    },
    "mem_total": {
        "auto_graph": False
    },
}

check_metrics["check_mk-esx_vsphere_hostsystem.mem_usage"] = mem_vsphere_hostsystem
check_metrics["check_mk-esx_vsphere_hostsystem.mem_usage_cluster"] = mem_vsphere_hostsystem

check_metrics["check_mk-ibm_svc_host"] = {
    "active": {
        "name": "hosts_active"
    },
    "inactive": {
        "name": "hosts_inactive"
    },
    "degraded": {
        "name": "hosts_degraded"
    },
    "offline": {
        "name": "hosts_offline"
    },
    "other": {
        "name": "hosts_other"
    },
}

juniper_mem = {
    "usage": {
        "name": "mem_used",
        "deprecated": True
    },
}
check_metrics["check_mk-juniper_screenos_mem"] = juniper_mem
check_metrics["check_mk-juniper_trpz_mem"] = juniper_mem

check_metrics["check_mk-ibm_svc_nodestats.iops"] = {
    "read": {
        "name": "disk_read_ios"
    },
    "write": {
        "name": "disk_write_ios"
    }
}

check_metrics["check_mk-openvpn_clients"] = {
    "in": {
        "name": "if_in_octets"
    },
    "out": {
        "name": "if_out_octets"
    }
}

check_metrics["check_mk-f5_bigip_interfaces"] = {
    "bytes_in": {
        "name": "if_in_octets"
    },
    "bytes_out": {
        "name": "if_out_octets"
    }
}

check_metrics["check_mk-f5_bigip_conns"] = {
    "conns": {
        "name": "connections"
    },
    "ssl_conns": {
        "name": "connections_ssl"
    },
}

check_metrics["check_mk-mbg_lantime_state"] = {
    "offset": {
        "name": "time_offset",
        "scale": 0.000001
    }
}  # convert us -> sec

check_metrics["check_mk-mbg_lantime_ng_state"] = {
    "offset": {
        "name": "time_offset",
        "scale": 0.000001
    }
}  # convert us -> sec

check_metrics["check_mk-systemtime"] = {
    "offset": {
        "name": "time_offset"
    },
}

check_metrics["check_mk-ntp"] = {
    "offset": {
        "name": "time_offset",
        "scale": m
    },
    "jitter": {
        "scale": m
    },
}

check_metrics["check_mk-chrony"] = {
    "offset": {
        "name": "time_offset",
        "scale": m
    },
}

check_metrics["check_mk-ntp.time"] = {
    "offset": {
        "name": "time_offset",
        "scale": m
    },
    "jitter": {
        "scale": m
    },
}

check_metrics["check_mk-adva_fsp_if"] = {
    "output_power": {
        "name": "output_signal_power_dbm"
    },
    "input_power": {
        "name": "input_signal_power_dbm"
    }
}

check_metrics["check_mk-allnet_ip_sensoric.tension"] = {
    "tension": {
        "name": "voltage_percent"
    },
}

check_metrics["check_mk-apache_status"] = {
    "Uptime": {
        "name": "uptime"
    },
    "IdleWorkers": {
        "name": "idle_workers"
    },
    "BusyWorkers": {
        "name": "busy_workers"
    },
    "IdleServers": {
        "name": "idle_servers"
    },
    "BusyServers": {
        "name": "busy_servers"
    },
    "OpenSlots": {
        "name": "open_slots"
    },
    "TotalSlots": {
        "name": "total_slots"
    },
    "CPULoad": {
        "name": "load1"
    },
    "ReqPerSec": {
        "name": "requests_per_second"
    },
    "BytesPerSec": {
        "name": "direkt_io"
    },
    "ConnsTotal": {
        "name": "connections"
    },
    "ConnsAsyncWriting": {
        "name": "connections_async_writing"
    },
    "ConnsAsyncKeepAlive": {
        "name": "connections_async_keepalive"
    },
    "ConnsAsyncClosing": {
        "name": "connections_async_closing"
    },
    "State_StartingUp": {
        "name": "apache_state_startingup"
    },
    "State_Waiting": {
        "name": "apache_state_waiting"
    },
    "State_Logging": {
        "name": "apache_state_logging"
    },
    "State_DNS": {
        "name": "apache_state_dns"
    },
    "State_SendingReply": {
        "name": "apache_state_sending_reply"
    },
    "State_ReadingRequest": {
        "name": "apache_state_reading_request"
    },
    "State_Closing": {
        "name": "apache_state_closing"
    },
    "State_IdleCleanup": {
        "name": "apache_state_idle_cleanup"
    },
    "State_Finishing": {
        "name": "apache_state_finishing"
    },
    "State_Keepalive": {
        "name": "apache_state_keep_alive"
    },
}

check_metrics["check_mk-ups_socomec_out_voltage"] = {
    "out_voltage": {
        "name": "voltage"
    },
}

check_metrics["check_mk-hp_blade_psu"] = {
    "output": {
        "name": "power"
    },
}

check_metrics["check_mk-apc_rackpdu_power"] = {
    "amperage": {
        "name": "current"
    },
}

check_metrics["check_mk-apc_ats_output"] = {
    "volt": {
        "name": "voltage"
    },
    "watt": {
        "name": "power"
    },
    "ampere": {
        "name": "current"
    },
    "load_perc": {
        "name": "output_load"
    }
}

check_metrics["check_mk-ups_out_load"] = {
    "out_load": {
        "name": "output_load"
    },
    "out_voltage": {
        "name": "voltage"
    },
}

check_metrics["check_mk-raritan_pdu_outletcount"] = {
    "outletcount": {
        "name": "connector_outlets"
    },
}

check_metrics["check_mk-docsis_channels_upstream"] = {
    "total": {
        "name": "total_modems"
    },
    "active": {
        "name": "active_modems"
    },
    "registered": {
        "name": "registered_modems"
    },
    "util": {
        "name": "channel_utilization"
    },
    "frequency": {
        "scale": 1000000.0
    },
    "codewords_corrected": {
        "scale": 100.0
    },
    "codewords_uncorrectable": {
        "scale": 100.0
    },
}

check_metrics["check_mk-docsis_channels_downstream"] = {
    "power": {
        "name": "downstream_power"
    },
}

check_metrics["check_mk-zfs_arc_cache"] = {
    "hit_ratio": {
        "name": "cache_hit_ratio",
    },
    "size": {
        "name": "caches",
    },
    "arc_meta_used": {
        "name": "zfs_metadata_used",
    },
    "arc_meta_limit": {
        "name": "zfs_metadata_limit",
    },
    "arc_meta_max": {
        "name": "zfs_metadata_max",
    },
}

check_metrics["check_mk-zfs_arc_cache.l2"] = {
    "l2_size": {
        "name": "zfs_l2_size"
    },
    "l2_hit_ratio": {
        "name": "zfs_l2_hit_ratio",
    },
}

check_metrics["check_mk-postgres_sessions"] = {
    "total": {
        "name": "total_sessions"
    },
    "running": {
        "name": "running_sessions"
    }
}

check_metrics["check_mk-fileinfo"] = {
    "size": {
        "name": "file_size"
    },
}

check_metrics["check_mk-fileinfo.groups"] = {
    "size": {
        "name": "total_file_size"
    },
    "size_smallest": {
        "name": "file_size_smallest"
    },
    "size_largest": {
        "name": "file_size_largest"
    },
    "count": {
        "name": "file_count"
    },
    "age_oldest": {
        "name": "file_age_oldest"
    },
    "age_newest": {
        "name": "file_age_newest"
    },
}

check_metrics["check_mk-postgres_stat_database.size"] = {
    "size": {
        "name": "database_size"
    },
}

check_metrics["check_mk-oracle_sessions"] = {
    "sessions": {
        "name": "running_sessions"
    },
}

check_metrics["check_mk-oracle_logswitches"] = {
    "logswitches": {
        "name": "logswitches_last_hour"
    },
}

check_metrics["check_mk-oracle_dataguard_stats"] = {
    "apply_lag": {
        "name": "database_apply_lag"
    },
}

check_metrics["check_mk-oracle_performance"] = {
    "DB_CPU": {
        "name": "oracle_db_cpu"
    },
    "DB_time": {
        "name": "oracle_db_time"
    },
    "buffer_hit_ratio": {
        "name": "oracle_buffer_hit_ratio"
    },
    "db_block_gets": {
        "name": "oracle_db_block_gets"
    },
    "db_block_change": {
        "name": "oracle_db_block_change"
    },
    "consistent_gets": {
        "name": "oracle_db_block_gets"
    },
    "physical_reads": {
        "name": "oracle_physical_reads"
    },
    "physical_writes": {
        "name": "oracle_physical_writes"
    },
    "free_buffer_wait": {
        "name": "oracle_free_buffer_wait"
    },
    "buffer_busy_wait": {
        "name": "oracle_buffer_busy_wait"
    },
    "library_cache_hit_ratio": {
        "name": "oracle_library_cache_hit_ratio"
    },
    "pinssum": {
        "name": "oracle_pins_sum"
    },
    "pinhitssum": {
        "name": "oracle_pin_hits_sum"
    },
}

check_metrics["check_mk-db2_logsize"] = {
    "~[_/]": {
        "name": "fs_used",
        "scale": MB,
        "deprecated": True
    },
    "fs_used": {
        "scale": MB
    },
    "fs_used_percent": {
        "auto_graph": False,
    },
}

check_metrics["check_mk-steelhead_connections"] = {
    "active": {
        "name": "fw_connections_active"
    },
    "established": {
        "name": "fw_connections_established"
    },
    "halfOpened": {
        "name": "fw_connections_halfopened"
    },
    "halfClosed": {
        "name": "fw_connections_halfclosed"
    },
    "passthrough": {
        "name": "fw_connections_passthrough"
    },
}

check_metrics["check_mk-oracle_tablespaces"] = {
    "size": {
        "name": "tablespace_size"
    },
    "used": {
        "name": "tablespace_used"
    },
    "max_size": {
        "name": "tablespace_max_size"
    },
}

check_metrics["check_mk-mssql_tablespaces"] = {
    "size": {
        "name": "database_size"
    },
    "unallocated": {
        "name": "unallocated_size"
    },
    "reserved": {
        "name": "reserved_size"
    },
    "data": {
        "name": "data_size"
    },
    "indexes": {
        "name": "indexes_size"
    },
    "unused": {
        "name": "unused_size"
    },
}

check_metrics["check_mk-f5_bigip_vserver"] = {
    "conn_rate": {
        "name": "connections_rate"
    },
}

check_metrics["check_mk-arcserve_backup"] = {
    "size": {
        "name": "backup_size",
    },
    "dirs": {
        "name": "directories",
    },
    "files": {
        "name": "file_count",
    }
}

check_metrics["check_mk-oracle_longactivesessions"] = {
    "count": {
        "name": "oracle_count",
    },
}

check_metrics["check_mk-oracle_rman"] = {
    "age": {
        "name": "backup_age"
    },
}

check_metrics["check_mk-veeam_client"] = {
    "totalsize": {
        "name": "backup_size"
    },
    "duration": {
        "name": "backup_duration"
    },
    "avgspeed": {
        "name": "backup_avgspeed"
    },
}

check_metrics["check_mk-cups_queues"] = {
    "jobs": {
        "name": "printer_queue"
    },
}

mq_translation = {
    "queue": {
        "name": "messages_in_queue"
    },
}
check_metrics['check_mk-mq_queues'] = mq_translation
check_metrics['check_mk-websphere_mq_channels'] = mq_translation
check_metrics['check_mk-websphere_mq_queues'] = mq_translation

check_metrics["check_mk-printer_pages"] = {
    "pages": {
        "name": "pages_total"
    },
}

check_metrics["check_mk-livestatus_status"] = {
    "host_checks": {
        "name": "host_check_rate"
    },
    "service_checks": {
        "name": "service_check_rate"
    },
    "connections": {
        "name": "livestatus_connect_rate"
    },
    "requests": {
        "name": "livestatus_request_rate"
    },
    "log_messages": {
        "name": "log_message_rate"
    },
}

check_metrics["check_mk-cisco_wlc_clients"] = {
    "clients": {
        "name": "connections"
    },
}

check_metrics["check_mk-cisco_qos"] = {
    "drop": {
        "name": "qos_dropped_bytes_rate"
    },
    "post": {
        "name": "qos_outbound_bytes_rate"
    },
}

check_metrics["check_mk-hivemanager_devices"] = {
    "clients_count": {
        "name": "connections"
    },
}

check_metrics["check_mk-ibm_svc_license"] = {
    "licensed": {
        "name": "licenses"
    },
}

check_metrics["check_mk-tsm_stagingpools"] = {
    "free": {
        "name": "tapes_free"
    },
    "tapes": {
        "name": "tapes_total"
    },
    "util": {
        "name": "tapes_util"
    }
}

check_metrics["check_mk-tsm_storagepools"] = {
    "used": {
        "name": "used_space"
    },
}

check_metrics["check_mk-hpux_tunables.shmseg"] = {
    "segments": {
        "name": "shared_memory_segments"
    },
}

check_metrics["check_mk-hpux_tunables.semmns"] = {
    "entries": {
        "name": "semaphores"
    },
}

check_metrics["check_mk-hpux_tunables.maxfiles_lim"] = {
    "files": {
        "name": "files_open"
    },
}

check_metrics["check_mk-win_dhcp_pools"] = {
    "free": {
        "name": "free_dhcp_leases"
    },
    "used": {
        "name": "used_dhcp_leases"
    },
    "pending": {
        "name": "pending_dhcp_leases"
    }
}

check_metrics["check_mk-lparstat_aix"] = {
    "sys": {
        "name": "system"
    },
    "wait": {
        "name": "io_wait"
    },
}

check_metrics["check_mk-netapp_fcpio"] = {
    "read": {
        "name": "disk_read_throughput"
    },
    "write": {
        "name": "disk_write_throughput"
    },
}

check_metrics["check_mk-netapp_api_vf_stats.traffic"] = {
    "read_bytes": {
        "name": "disk_read_throughput"
    },
    "write_bytes": {
        "name": "disk_write_throughput"
    },
    "read_ops": {
        "name": "disk_read_ios"
    },
    "write_ops": {
        "name": "disk_write_ios"
    },
}

check_metrics["check_mk-job"] = {
    "reads": {
        "name": "disk_read_throughput"
    },
    "writes": {
        "name": "disk_write_throughput"
    },
    "real_time": {
        "name": "job_duration"
    },
}

ps_translation = {
    "count": {
        "name": "processes"
    },
    "vsz": {
        "name": "process_virtual_size",
        "scale": KB,
    },
    "rss": {
        "name": "process_resident_size",
        "scale": KB,
    },
    "pcpu": {
        "name": "util"
    },
    "pcpuavg": {
        "name": "util_average"
    },
}

check_metrics["check_mk-smart.stats"] = {
    "Power_On_Hours": {
        "name": "uptime",
        "scale": 3600
    },
    "Power_Cycle_Count": {
        "name": "harddrive_power_cycles"
    },
    "Reallocated_Sector_Ct": {
        "name": "harddrive_reallocated_sectors"
    },
    "Reallocated_Event_Count": {
        "name": "harddrive_reallocated_events"
    },
    "Spin_Retry_Count": {
        "name": "harddrive_spin_retries"
    },
    "Current_Pending_Sector": {
        "name": "harddrive_pending_sectors"
    },
    "Command_Timeout": {
        "name": "harddrive_cmd_timeouts"
    },
    "End-to-End_Error": {
        "name": "harddrive_end_to_end_errors"
    },
    "Reported_Uncorrect": {
        "name": "harddrive_uncorrectable_errors"
    },
    "UDMA_CRC_Error_Count": {
        "name": "harddrive_udma_crc_errors"
    },
    "CRC_Error_Count": {
        "name": "harddrive_crc_errors",
    },
    "Uncorrectable_Error_Cnt": {
        "name": "harddrive_uncorrectable_errors",
    },
    "Power_Cycles": {
        "name": "harddrive_power_cycles"
    },
    "Media_and_Data_Integrity_Errors": {
        "name": "nvme_media_and_data_integrity_errors"
    },
    "Error_Information_Log_Entries": {
        "name": "nvme_error_information_log_entries"
    },
    "Critical_Warning": {
        "name": "nvme_critical_warning"
    },
    "Available_Spare": {
        "name": "nvme_available_spare"
    },
    "Percentage_Used": {
        "name": "nvme_spare_percentage_used"
    },
    "Data_Units_Read": {
        "name": "nvme_data_units_read"
    },
    "Data_Units_Written": {
        "name": "nvme_data_units_written"
    },
}

check_metrics["check_mk-ps"] = ps_translation
check_metrics["check_mk-ps.perf"] = ps_translation

check_metrics["check_mk-mssql_counters.sqlstats"] = {
    "batch_requests/sec": {
        "name": "requests_per_second"
    },
    "sql_compilations/sec": {
        "name": "requests_per_second"
    },
    "sql_re-compilations/sec": {
        "name": "requests_per_second"
    },
}

check_metrics["check_mk-mssql_counters.file_sizes"] = {
    "log_files": {
        "name": "log_files_total"
    },
}

cisco_mem_translation = {
    "mem_used": {
        "name": "mem_used_percent",
        "deprecated": True
    },
}
check_metrics["check_mk-cisco_cpu_memory"] = cisco_mem_translation
check_metrics["check_mk-cisco_sys_mem"] = cisco_mem_translation

cisco_mem_translation_with_trend = dict(cisco_mem_translation)
cisco_mem_translation_with_trend.update({
    "growth": {
        "name": "mem_growth"
    },
    "trend": {
        "name": "mem_trend"
    },
})
check_metrics["check_mk-cisco_mem"] = cisco_mem_translation_with_trend
check_metrics["check_mk-cisco_mem_asa"] = cisco_mem_translation_with_trend
check_metrics["check_mk-cisco_mem_asa64"] = cisco_mem_translation_with_trend

check_metrics["check_mk-fortigate_sessions_base"] = {
    "session": {
        "name": "active_sessions"
    },
}

#.
#   .--Perf-O-Meters-------------------------------------------------------.
#   |  ____            __        ___        __  __      _                  |
#   | |  _ \ ___ _ __ / _|      / _ \      |  \/  | ___| |_ ___ _ __ ___   |
#   | | |_) / _ \ '__| |_ _____| | | |_____| |\/| |/ _ \ __/ _ \ '__/ __|  |
#   | |  __/  __/ |  |  _|_____| |_| |_____| |  | |  __/ ||  __/ |  \__ \  |
#   | |_|   \___|_|  |_|        \___/      |_|  |_|\___|\__\___|_|  |___/  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Definition of Perf-O-Meters                                         |
#   '----------------------------------------------------------------------'

# If multiple Perf-O-Meters apply, the first applicable Perf-O-Meter in the list will
# be the one appearing in the GUI.

# Types of Perf-O-Meters:
# linear      -> multiple values added from left to right
# logarithmic -> one value in a logarithmic scale
# dual        -> two Perf-O-Meters next to each other, the first one from right to left
# stacked     -> two Perf-O-Meters of type linear, logarithmic or dual, stack vertically
# The label of dual and stacked is taken from the definition of the contained Perf-O-Meters

# Optional keys:
# "sort_group" -> When sorting perfometer the first criteria used is either this optional performeter
#                 group or the perfometer ID. The sort_group can be used to group different perfometers
#                 which show equal data for sorting them together in a single sort domain.

perfometer_info.append({
    "type": "dual",
    "perfometers": [{
        "type": "logarithmic",
        "metric": "tcp_active_sessions",
        "half_value": 4,
        "exponent": 2,
    }, {
        "type": "logarithmic",
        "metric": "udp_active_sessions",
        "half_value": 4,
        "exponent": 2,
    }],
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "parts_per_million",
    "half_value": 50.0,
    "exponent": 2,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["mem_used_percent"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["cpu_mem_used_percent"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["ap_devices_drifted", "ap_devices_not_responding"],
    "total": "ap_devices_total",
})

perfometer_info.append({
    "type": "linear",
    "segments": ["execution_time"],
    "total": 90.0,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "session_rate",
    "half_value": 50.0,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "uptime",
    "half_value": 2592000.0,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "age",
    "half_value": 2592000.0,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "runtime",
    "half_value": 864000.0,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "last_updated",
    "half_value": 40.0,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "job_duration",
    "half_value": 120.0,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "response_time",
    "half_value": 10,
    "exponent": 4,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "mails_received_time",
    "half_value": 5,
    "exponent": 3,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["mem_perm_used"],
    "total": "mem_perm_used:max",
})

perfometer_info.append({
    "type": "linear",
    "segments": ["mem_heap"],
    "total": "mem_heap:max",
})

perfometer_info.append({
    "type": "linear",
    "segments": ["mem_nonheap"],
    "total": "mem_nonheap:max",
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "pressure",
    "half_value": 0.5,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "pressure_pa",
    "half_value": 10,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "cifs_share_users",
    "half_value": 10,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "connector_outlets",
    "half_value": 20,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "licenses",
    "half_value": 500,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "sync_latency",
    "half_value": 5,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "mail_latency",
    "half_value": 5,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "backup_size",
    "half_value": 150 * GB,
    "exponent": 2.0,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "fw_connections_active",
    "half_value": 100,
    "exponent": 2,
})

perfometer_info.append({
    "type": "stacked",
    "perfometers": [{
        "type": "logarithmic",
        "metric": "checkpoint_age",
        "half_value": 86400,
        "exponent": 2,
    }, {
        "type": "logarithmic",
        "metric": "backup_age",
        "half_value": 86400,
        "exponent": 2,
    }],
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "backup_age",
    "half_value": 86400,
    "exponent": 2,
})

perfometer_info.append({
    "type": "stacked",
    "perfometers": [{
        "type": "logarithmic",
        "metric": "read_latency",
        "half_value": 5,
        "exponent": 2,
    }, {
        "type": "logarithmic",
        "metric": "write_latency",
        "half_value": 5,
        "exponent": 2,
    }],
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "logswitches_last_hour",
    "half_value": 15,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "oracle_count",
    "half_value": 250,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "database_apply_lag",
    "half_value": 2500,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "processes",
    "half_value": 100,
    "exponent": 2,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["total_cache_usage"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "stacked",
    "perfometers": [{
        "type": "logarithmic",
        "metric": "mem_heap",
        "half_value": 100 * MB,
        "exponent": 2,
    }, {
        "type": "logarithmic",
        "metric": "mem_nonheap",
        "half_value": 100 * MB,
        "exponent": 2,
    }],
})

perfometer_info.append({
    "type": "stacked",
    "perfometers": [{
        "type": "linear",
        "segments": ["threads_idle"],
        "total": "threads_idle:max",
    }, {
        "type": "linear",
        "segments": ["threads_busy"],
        "total": "threads_busy:max",
    }],
})

perfometer_info.append({"type": "logarithmic", "metric": "rta", "half_value": 0.1, "exponent": 4})

perfometer_info.append({"type": "logarithmic", "metric": "rtt", "half_value": 0.1, "exponent": 4})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "load1",
    "half_value": 4.0,
    "exponent": 2.0
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "temp",
    "half_value": 40.0,
    "exponent": 1.2
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "dedup_rate",
    "half_value": 30.0,
    "exponent": 1.2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "major_page_faults",
    "half_value": 1000.0,
    "exponent": 2.0
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "threads",
    "half_value": 400.0,
    "exponent": 2.0
})

perfometer_info.append({
    "type": "linear",
    "segments": ["user", "system", "idle", "nice"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["user", "system", "idle", "io_wait"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["user", "system", "io_wait"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["fpga_util",],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["overall_util",],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["pci_io_util",],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["memory_util",],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["util",],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["generic_util",],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["util1",],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["user", "system", "streams"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["citrix_load"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "database_size",
    "half_value": GB,
    "exponent": 5.0,
})

# Filesystem check with over-provisioning
perfometer_info.append({
    "type": "linear",
    "condition": "fs_provisioning(%),100,>",
    "segments": [
        "fs_used(%)",
        "100,fs_used(%),-#e3fff9",
        "fs_provisioning(%),100.0,-#ffc030",
    ],
    "total": "fs_provisioning(%)",
    "label": ("fs_used(%)", "%"),
})

# Filesystem check with provisioning, but not over-provisioning
perfometer_info.append({
    "type": "linear",
    "condition": "fs_provisioning(%),100,<=",
    "segments": [
        "fs_used(%)",
        "fs_provisioning(%),fs_used(%),-#ffc030",
        "100,fs_provisioning(%),fs_used(%),-,-#e3fff9",
    ],
    "total": 100,
    "label": ("fs_used(%)", "%"),
})

# Filesystem check without overcommittment
perfometer_info.append({
    "type": "linear",
    "condition": "fs_used,uncommitted,+,fs_size,<",
    "segments": [
        "fs_used",
        "uncommitted",
        "fs_size,fs_used,-,uncommitted,-#e3fff9",  # free
        "0.1#559090",  # fs_size marker
    ],
    "total": "fs_size",
    "label": ("fs_used(%)", "%"),
})

# Filesystem check with overcommittment
perfometer_info.append({
    "type": "linear",
    "condition": "fs_used,uncommitted,+,fs_size,>=",
    "segments": [
        "fs_used",
        "fs_size,fs_used,-#e3fff9",  # free
        "0.1#559090",  # fs_size marker
        "overprovisioned,fs_size,-#ffa000",  # overcommittment
    ],
    "total": "overprovisioned",
    "label": (
        "fs_used,fs_used,uncommitted,+,/,100,*",  # percent used scaled
        "%",
    ),
})

# Filesystem without over-provisioning
perfometer_info.append({
    "type": "linear",
    "segments": [
        "fs_used(%)",
        "100.0,fs_used(%),-#e3fff9",
    ],
    "total": 100,
    "label": ("fs_used(%)", "%"),
})

perfometer_info.append({
    "type": "linear",
    "segments": ["mem_used", "swap_used", "caches", "mem_free", "swap_free"],
    "label": ("mem_used,swap_used,+,mem_total,/,100,*", "%"),
})

perfometer_info.append({
    "type": "linear",
    "segments": ["mem_used"],
    "total": "mem_total",
})

perfometer_info.append({
    "type": "linear",
    "segments": ["mem_used(%)"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["mem_used"],
    "total": "mem_used:max",
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "mem_used",
    "half_value": GB,
    "exponent": 4.0,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "time_offset",
    "half_value": 1.0,
    "exponent": 10.0,
})

perfometer_info.append({
    "type": "stacked",
    "perfometers": [
        {
            "type": "logarithmic",
            "metric": "tablespace_wasted",
            "half_value": 1000000,
            "exponent": 2,
        },
        {
            "type": "logarithmic",
            "metric": "indexspace_wasted",
            "half_value": 1000000,
            "exponent": 2,
        },
    ],
})

perfometer_info.append({
    "type": "linear",
    "segments": ["running_sessions"],
    "total": "total_sessions",
})

# TODO total : None?
perfometer_info.append({
    "type": "linear",
    "segments": ["shared_locks", "exclusive_locks"],
    "total": None,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "connections",
    "half_value": 50,
    "exponent": 2
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "connection_time",
    "half_value": 0.2,
    "exponent": 2,
})

perfometer_info.append({
    "type": "dual",
    "perfometers": [
        {
            "type": "logarithmic",
            "metric": "input_signal_power_dbm",
            "half_value": 4,
            "exponent": 2,
        },
        {
            "type": "logarithmic",
            "metric": "output_signal_power_dbm",
            "half_value": 4,
            "exponent": 2,
        },
    ],
})

perfometer_info.append({
    "type": "dual",
    "perfometers": [
        {
            "type": "logarithmic",
            "metric": "if_in_bps",
            "half_value": 5000000,
            "exponent": 5,
        },
        {
            "type": "logarithmic",
            "metric": "if_out_bps",
            "half_value": 5000000,
            "exponent": 5,
        },
    ],
})

perfometer_info.append({
    "type": "dual",
    "perfometers": [
        {
            "type": "logarithmic",
            "metric": "if_in_octets",
            "half_value": 5000000,
            "exponent": 5,
        },
        {
            "type": "logarithmic",
            "metric": "if_out_octets",
            "half_value": 5000000,
            "exponent": 5,
        },
    ],
})

perfometer_info.append({
    "type": "dual",
    "perfometers": [
        {
            "type": "logarithmic",
            "metric": "if_out_unicast_octets,if_out_non_unicast_octets,+",
            "half_value": 5000000,
            "exponent": 5,
        },
        {
            "type": "logarithmic",
            "metric": "if_in_octets",
            "half_value": 5000000,
            "exponent": 5,
        },
    ],
})

perfometer_info.append({
    "type": "dual",
    "perfometers": [
        {
            "type": "logarithmic",
            "metric": "read_blocks",
            "half_value": 50000000,
            "exponent": 2,
        },
        {
            "type": "logarithmic",
            "metric": "write_blocks",
            "half_value": 50000000,
            "exponent": 2,
        },
    ],
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "running_sessions",
    "half_value": 10,
    "exponent": 2
})

perfometer_info.append({
    "type": "dual",
    "perfometers": [
        {
            "type": "logarithmic",
            "metric": "deadlocks",
            "half_value": 50,
            "exponent": 2,
        },
        {
            "type": "logarithmic",
            "metric": "lockwaits",
            "half_value": 50,
            "exponent": 2,
        },
    ],
})

# TODO: max fehlt
perfometer_info.append({
    "type": "linear",
    "segments": ["sort_overflow"],
})

perfometer_info.append({
    "type": "linear",
    "segments": ["tablespace_used"],
    "total": "tablespace_max_size",
})

perfometer_info.append({
    "type": "stacked",
    "perfometers": [
        {
            "type": "dual",
            "perfometers": [
                {
                    "type": "linear",
                    "label": None,
                    "segments": ["total_hitratio"],
                    "total": 100
                },
                {
                    "type": "linear",
                    "label": None,
                    "segments": ["data_hitratio"],
                    "total": 100
                },
            ],
        },
        {
            "type": "dual",
            "perfometers": [
                {
                    "type": "linear",
                    "label": None,
                    "segments": ["index_hitratio"],
                    "total": 100
                },
                {
                    "type": "linear",
                    "label": None,
                    "segments": ["xda_hitratio"],
                    "total": 100
                },
            ],
        },
    ],
})

perfometer_info.append({
    "type": "linear",
    "segments": ["output_load"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "power",
    "half_value": 1000,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "current",
    "half_value": 10,
    "exponent": 4,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "voltage",
    "half_value": 220.0,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "energy",
    "half_value": 10000,
    "exponent": 3,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["voltage_percent"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["humidity"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "stacked",
    "perfometers": [
        {
            "type": "logarithmic",
            "metric": "requests_per_second",
            "half_value": 10,
            "exponent": 5,
        },
        {
            "type": "logarithmic",
            "metric": "busy_workers",
            "half_value": 10,
            "exponent": 2,
        },
    ],
})

perfometer_info.append({
    "type": "linear",
    "segments": ["cache_hit_ratio"],
    "total": 100,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["varnish_worker_thread_ratio"],
    "total": 100,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["varnish_backend_success_ratio"],
    "total": 100,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["zfs_l2_hit_ratio"],
    "total": 100,
})

perfometer_info.append({
    "type": "stacked",
    "perfometers": [
        {
            "type": "logarithmic",
            "metric": "signal_noise",
            "half_value": 50.0,
            "exponent": 2.0,
        },
        {
            "type": "linear",
            "segments": ["codewords_corrected", "codewords_uncorrectable"],
            "total": 1.0,
        },
    ],
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "signal_noise",
    "half_value": 50.0,
    "exponent": 2.0
})  # Fallback if no codewords are available

perfometer_info.append({
    "type": "dual",
    "perfometers": [
        {
            "type": "logarithmic",
            "metric": "disk_read_throughput",
            "half_value": 5000000,
            "exponent": 10,
        },
        {
            "type": "logarithmic",
            "metric": "disk_write_throughput",
            "half_value": 5000000,
            "exponent": 10,
        },
    ],
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "disk_ios",
    "half_value": 30,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "disk_capacity",
    "half_value": 25 * TB,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "printer_queue",
    "half_value": 10,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "pages_total",
    "half_value": 60000,
    "exponent": 2,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["supply_toner_cyan"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["supply_toner_magenta"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["supply_toner_yellow"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["supply_toner_black"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["supply_toner_other"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["smoke_ppm"],
    "total": 10,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["smoke_perc"],
    "total": 100,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["health_perc"],
    "total": 100,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["deviation_calibration_point"],
    "total": 10,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["deviation_airflow"],
    "total": 10,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "airflow",
    "half_value": 300,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "fluidflow",
    "half_value": 0.2,
    "exponent": 5,
})

perfometer_info.append({
    "type": "stacked",
    "perfometers": [
        {
            "type": "logarithmic",
            "metric": "direct_io",
            "half_value": 25,
            "exponent": 2,
        },
        {
            "type": "logarithmic",
            "metric": "buffered_io",
            "half_value": 25,
            "exponent": 2,
        },
    ],
})

# TODO: :max should be the default?
perfometer_info.append({
    "type": "linear",
    "segments": ["free_dhcp_leases"],
    "total": "free_dhcp_leases:max",
})

perfometer_info.append({
    "type": "stacked",
    "perfometers": [
        {
            "type": "logarithmic",
            "metric": "host_check_rate",
            "half_value": 50,
            "exponent": 5,
        },
        {
            "type": "logarithmic",
            "metric": "service_check_rate",
            "half_value": 200,
            "exponent": 5,
        },
    ],
})

perfometer_info.append({
    "type": "stacked",
    "perfometers": [
        {
            "type": "logarithmic",
            "metric": "normal_updates",
            "half_value": 10,
            "exponent": 2,
        },
        {
            "type": "logarithmic",
            "metric": "security_updates",
            "half_value": 10,
            "exponent": 2,
        },
    ],
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "registered_phones",
    "half_value": 50,
    "exponent": 3,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "call_legs",
    "half_value": 10,
    "exponent": 2,
})

perfometer_info.append({
    "type": "stacked",
    "perfometers": [{
        "type": "logarithmic",
        "metric": "mail_queue_deferred_length",
        "half_value": 10000,
        "exponent": 5,
    }, {
        "type": "logarithmic",
        "metric": "mail_queue_active_length",
        "half_value": 10000,
        "exponent": 5,
    }],
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "mail_queue_deferred_length",
    "half_value": 10000,
    "exponent": 5
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "messages_inbound,messages_outbound,+",
    "half_value": 100,
    "exponent": 5,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["tapes_util"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "dual",
    "perfometers": [
        {
            "type": "linear",
            "segments": ["qos_dropped_bytes_rate"],
            "total": "qos_dropped_bytes_rate:max"
        },
        {
            "type": "linear",
            "segments": ["qos_outbound_bytes_rate"],
            "total": "qos_outbound_bytes_rate:max"
        },
    ],
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "semaphore_ids",
    "half_value": 50,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "segments",
    "half_value": 10,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "semaphores",
    "half_value": 2500,
    "exponent": 2,
})

perfometer_info.append({
    "type": "dual",
    "perfometers": [
        {
            "type": "logarithmic",
            "metric": "fc_rx_bytes",
            "half_value": 30 * MB,
            "exponent": 3,
        },
        {
            "type": "logarithmic",
            "metric": "fc_tx_bytes",
            "half_value": 30 * MB,
            "exponent": 3,
        },
    ],
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "request_rate",
    "half_value": 100,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "mem_pages_rate",
    "half_value": 5000,
    "exponent": 2,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["storage_processor_util"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["active_vpn_tunnels"],
    "total": "active_vpn_tunnels:max"
})


def register_hop_perfometers():
    for x in reversed(range(1, MAX_NUMBER_HOPS)):
        perfometer_info.append({
            "type": "dual",
            "perfometers": [
                {
                    "type": "linear",
                    "segments": ["hop_%d_pl" % x],
                    "total": 100.0,
                },
                {
                    "type": "logarithmic",
                    "metric": "hop_%d_rta" % x,
                    "half_value": 0.1,
                    "exponent": 4
                },
            ],
        })


register_hop_perfometers()

perfometer_info.append({
    "type": "logarithmic",
    "metric": "oracle_db_cpu",
    "half_value": 50.0,
    "exponent": 2,
})


def get_skype_mobile_perfometer_segments():
    return ["active_sessions_%s" % device for device, _name, _color in skype_mobile_devices]


perfometer_info.append({
    "type": "linear",
    "segments": get_skype_mobile_perfometer_segments(),
    # there is no limit and no way to determine the max so far for
    # all segments
})

perfometer_info.append({
    "type": "linear",
    "segments": ["filehandler_perc"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["capacity_perc"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "fan",
    "half_value": 3000,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "emcvnx_consumed_capacity",
    "half_value": 20 * TB,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "emcvnx_dedupl_remaining_size",
    "half_value": 20 * TB,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "emcvnx_move_completed",
    "half_value": 250 * GB,
    "exponent": 3,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["read_hits"],
    "total": 100.0,
})

perfometer_info.append({
    'type': 'linear',
    'segments': ['active_vms'],
    'total': 200,
})

perfometer_info.append({
    'type': 'logarithmic',
    'metric': 'days',
    'half_value': 100,
    'exponent': 2,
})

perfometer_info.append({
    'type': 'linear',
    'segments': ['quarantine'],
    'total': 100,
})

perfometer_info.append({
    'type': 'logarithmic',
    'metric': 'total_rate',
    'half_value': 50.0,
    'exponent': 2.0,
})

perfometer_info.append({
    'type': 'logarithmic',
    'metric': 'bypass_rate',
    'half_value': 2.0,
    'exponent': 2.0,
})

perfometer_info.append({
    'type': 'logarithmic',
    'metric': 'fireeye_stat_attachment',
    'half_value': 50.0,
    'exponent': 2.0,
})

perfometer_info.append({
    'type': 'logarithmic',
    'metric': 'messages_in_queue',
    'half_value': 1.0,
    'exponent': 2.0,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "queue",
    "half_value": 80,
    "exponent": 2,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["connections_perc_used"],
    "total": 100,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "used_space",
    "half_value": GB,
    "exponent": 2,
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "aws_overall_hosts_health_perc",
    "half_value": 100,
    "exponent": 2,
})

perfometer_info.append({
    'type': 'logarithmic',
    'metric': 'elapsed_time',
    'half_value': 1.0,
    'exponent': 2.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["license_percentage"],
    "total": 100.0,
    "color": "16/a",
})

perfometer_info.append({
    "type": "linear",
    "segments": ["license_percentage"],
    "total": 100.0,
    "color": "16/a",
})

perfometer_info.append({
    'type': 'stacked',
    'perfometers': [{
        'type': 'logarithmic',
        'metric': 'elasticsearch_size_rate',
        'half_value': 5000,
        'exponent': 2,
    }, {
        'type': 'logarithmic',
        'metric': 'elasticsearch_count_rate',
        'half_value': 10,
        'exponent': 2,
    }],
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "number_of_pending_tasks_rate",
    "half_value": 10,
    "exponent": 2,
    "unit": "count",
})

perfometer_info.append({
    'type': 'dual',
    'perfometers': [{
        'type': 'linear',
        'segments': ['active_primary_shards'],
        'total': 'active_shards',
    }, {
        'type': 'linear',
        'segments': ['active_shards'],
        'total': 'active_shards',
    }],
})

perfometer_info.append({
    "type": "linear",
    "segments": ["active_shards_percent_as_number"],
    "total": 100.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": [
        "docker_running_containers",
        "docker_paused_containers",
        "docker_stopped_containers",
    ],
    "total": "docker_all_containers",
})

perfometer_info.append({
    'type': 'logarithmic',
    'metric': 'docker_size',
    'half_value': GB,
    'exponent': 2.0,
})

perfometer_info.append({
    'type': 'logarithmic',
    'metric': 'nimble_read_latency_total',
    'half_value': 10,
    'exponent': 2.0,
})

perfometer_info.append({
    'type': 'logarithmic',
    'metric': 'nimble_write_latency_total',
    'half_value': 10,
    'exponent': 2.0,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["fragmentation"],
})

perfometer_info.append({
    "type": "logarithmic",
    "metric": "items_count",
    "half_value": 1000,
    "exponent": 2,
})

perfometer_info.append({
    "type": "linear",
    "segments": ["log_file_utilization"],
    "total": 100.0,
})

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

# beware: the order of the list elements of graph_info is actually important.
# It determines the order of graphs of a service, which in turn is used by
# the report definitions to determine which graph to include.

# Order of metrics in graph recipes important if you use only 'area':
# The first one must be the bigger one, then descending.
# Example: ('tablespace_size', 'area'),
#          ('tablespace_used', 'area')

graph_info["fan_speed"] = {"title": _("Fan speed"), "metrics": [("fan_speed", "area"),]}

graph_info["aws_ec2_running_ondemand_instances"] = {
    "title": _("Total running On-Demand Instances"),
    "metrics": [('aws_ec2_running_ondemand_instances_total', 'line')] +
               [('aws_ec2_running_ondemand_instances_%s' % inst_type, "stack")
                for inst_type in AWSEC2InstTypes],
    "optional_metrics": [
        'aws_ec2_running_ondemand_instances_%s' % inst_type for inst_type in AWSEC2InstTypes
    ],
}

graph_info["context_switches"] = {
    "title": _("Context switches"),
    "metrics": [
        ("vol_context_switches", "area"),
        ("invol_context_switches", "stack"),
    ],
}

graph_info["busy_and_idle_workers"] = {
    "title": _("Busy and idle workers"),
    "metrics": [
        ("busy_workers", "area"),
        ("idle_workers", "stack"),
    ],
}

graph_info["busy_and_idle_servers"] = {
    "title": _("Busy and idle servers"),
    "metrics": [
        ("busy_servers", "area"),
        ("idle_servers", "stack"),
    ],
}

graph_info["total_and_open_slots"] = {
    "title": _("Total and open slots"),
    "metrics": [
        ("total_slots", "area"),
        ("open_slots", "area"),
    ],
}

graph_info["connections"] = {
    "title": _("Connections"),
    "metrics": [
        ("connections", "area"),
        ("connections_async_writing", "area"),
        ("connections_async_keepalive", "stack"),
        ("connections_async_closing", "stack"),
    ],
    "optional_metrics": [
        "connections_async_writing",
        "connections_async_keepalive",
        "connections_async_closing",
    ],
    "scalars": [
        "connections:warn",
        "connections:crit",
    ],
}

graph_info["apache_status"] = {
    "title": _("Apache status"),
    "metrics": [
        ("apache_state_startingup", "area"),
        ("apache_state_waiting", "stack"),
        ("apache_state_logging", "stack"),
        ("apache_state_dns", "stack"),
        ("apache_state_sending_reply", "stack"),
        ("apache_state_reading_request", "stack"),
        ("apache_state_closing", "stack"),
        ("apache_state_idle_cleanup", "stack"),
        ("apache_state_finishing", "stack"),
        ("apache_state_keep_alive", "stack"),
    ],
}

graph_info["battery_currents"] = {
    "title": _("Battery currents"),
    "metrics": [
        ("battery_current", "area"),
        ("current", "stack"),
    ],
}

graph_info["battery_capacity"] = {
    "metrics": [("battery_capacity", "area"),],
    "range": (0, 100),
}

graph_info["qos_class_traffic"] = {
    "title": _("QoS class traffic"),
    "metrics": [
        ("qos_outbound_bytes_rate,8,*@bits/s", "area", _("QoS outbound bits")),
        ("qos_dropped_bytes_rate,8,*@bits/s", "-area", _("QoS dropped bits")),
    ],
    "range": ("qos_dropped_bytes_rate:max,8,*,-1,*", "qos_outbound_bytes_rate:max,8,*")
}

graph_info["read_and_written_blocks"] = {
    "title": _("Read and written blocks"),
    "metrics": [
        ("read_blocks", "area"),
        ("write_blocks", "-area"),
    ],
}

graph_info["rmon_packets_per_second"] = {
    "title": _("RMON packets per second"),
    "metrics": [
        ("broadcast_packets", "area"),
        ("multicast_packets", "stack"),
        ("rmon_packets_63", "stack"),
        ("rmon_packets_127", "stack"),
        ("rmon_packets_255", "stack"),
        ("rmon_packets_511", "stack"),
        ("rmon_packets_1023", "stack"),
        ("rmon_packets_1518", "stack"),
    ],
}

graph_info["threads"] = {
    "title": _("Threads"),
    "metrics": [
        ("threads", "area"),
        ("threads_daemon", "stack"),
        ("threads_max", "stack"),
    ],
}

graph_info["thread_usage"] = {
    "metrics": [("thread_usage", "area"),],
    "scalars": ["thread_usage:warn", "thread_usage:crit"],
    "range": (0, 100),
}

graph_info["threadpool"] = {
    "title": _("Threadpool"),
    "metrics": [
        ("threads_busy", "stack"),
        ("threads_idle", "stack"),
    ],
}

graph_info["disk_rw_latency"] = {
    "title": _("Disk latency"),
    "metrics": [("disk_read_latency", "area"), ("disk_write_latency", "-area")],
}

# TODO: is this still used?
graph_info["disk_latency"] = {
    "title": _("Disk latency"),
    "metrics": [("read_latency", "area"), ("write_latency", "-area")],
}

graph_info["read_write_queue_length"] = {
    "title": _("Read / Write queue length"),
    "metrics": [("disk_read_ql", "area"), ("disk_write_ql", "-area")],
}

graph_info["backup_time"] = {
    "title": _("Backup time"),
    "metrics": [("checkpoint_age", "area"), ("backup_age", "stack")],
}

graph_info["time_offset"] = {
    "title": _("Time offset"),
    "metrics": [("time_offset", "area"), ("jitter", "line")],
    "scalars": [
        ("time_offset:crit", _("Upper critical level")),
        ("time_offset:warn", _("Upper warning level")),
        ("0,time_offset:warn,-", _("Lower warning level")),
        ("0,time_offset:crit,-", _("Lower critical level")),
    ],
    "range": ("0,time_offset:crit,-", "time_offset:crit"),
    "optional_metrics": ["jitter"],
}

graph_info["total_cache_usage"] = {
    "metrics": [("total_cache_usage", "area")],
    "range": (0, 100),
}

graph_info["write_cache_usage"] = {
    "metrics": [("write_cache_usage", "area")],
    "range": (0, 100),
}

graph_info["zfs_meta_data"] = {
    "title": _("ZFS meta data"),
    "metrics": [
        ("zfs_metadata_max", "area"),
        ("zfs_metadata_used", "area"),
        ("zfs_metadata_limit", "line"),
    ],
}

graph_info["cache_hit_ratio"] = {
    "title": _("Cache hit ratio"),
    "metrics": [
        ("cache_hit_ratio", "area"),
        ("prefetch_metadata_hit_ratio", "line"),
        ("prefetch_data_hit_ratio", "area"),
    ],
}

graph_info["citrix_licenses"] = {
    "title": _("Citrix licenses"),
    "metrics": [("licenses", "area"),],
    "scalars": [
        "licenses:warn",
        "licenses:crit",
        ("licenses:max#000000", "Installed licenses"),
    ],
    "range": (0, "licenses:max"),
}

graph_info["citrix_serverload"] = {
    "title": _("Citrix Serverload"),
    "metrics": [("citrix_load", "area"),],
    "range": (0, 100),
}

graph_info["k8s_resources.pods"] = {
    "title": _("Pod resources"),
    "metrics": [
        ("k8s_pods_capacity", "area"),
        ("k8s_pods_allocatable", "area"),
        ("k8s_pods_request", "area"),
    ],
}

graph_info["k8s_resources.cpu"] = {
    "title": _("CPU resources"),
    "metrics": [
        ("k8s_cpu_capacity", "area"),
        ("k8s_cpu_allocatable", "area"),
        ("k8s_cpu_limit", "area"),
        ("k8s_cpu_request", "area"),
    ],
    "optional_metrics": ["k8s_cpu_capacity", "k8s_cpu_allocatable", "k8s_cpu_limit"],
}

graph_info["k8s_resources.memory"] = {
    "title": _("Memory resources"),
    "metrics": [
        ("k8s_memory_capacity", "area"),
        ("k8s_memory_allocatable", "area"),
        ("k8s_memory_limit", "area"),
        ("k8s_memory_request", "area"),
    ],
    "optional_metrics": ["k8s_memory_capacity", "k8s_memory_allocatable", "k8s_memory_limit"],
}

graph_info["k8s_pod_container"] = {
    "title": _("Ready containers"),
    "metrics": [
        ("docker_all_containers", "line"),
        ("ready_containers", "area"),
    ],
}

graph_info["replicas"] = {
    "title": _("Replicas"),
    "metrics": [
        ("ready_replicas", "area"),
        ("total_replicas", "line"),
    ],
    "scalars": ["ready_replicas:crit",]
}

graph_info["docker_containers"] = {
    "title": _("Docker Containers"),
    "metrics": [
        ("docker_running_containers", "area"),
        ("docker_paused_containers", "stack"),
        ("docker_stopped_containers", "stack"),
        ("docker_all_containers", "line"),
    ],
}

graph_info["docker_df"] = {
    "title": _("Docker Disk Usage"),
    "metrics": [
        ("docker_size", "area"),
        ("docker_reclaimable", "area"),
    ],
}

graph_info["docker_df_count"] = {
    "title": _("Docker Disk Usage Count"),
    "metrics": [
        ("docker_count", "area"),
        ("docker_active", "area"),
    ],
}

graph_info["used_cpu_time"] = {
    "title": _("Used CPU Time"),
    "metrics": [
        ("user_time", "area"),
        ("children_user_time", "stack"),
        ("system_time", "stack"),
        ("children_system_time", "stack"),
        ("user_time,children_user_time,system_time,children_system_time,+,+,+#888888", "line",
         _("Total")),
    ],
    "omit_zero_metrics": True,
    "conflicting_metrics": ["cmk_time_agent", "cmk_time_snmp", "cmk_time_ds"],
}

graph_info["cmk_cpu_time_by_phase"] = {
    "title": _("Time usage by phase"),
    "metrics": [
        ("user_time,children_user_time,+", "stack", _("CPU time in user space")),
        ("system_time,children_system_time,+", "stack", _("CPU time in operating system")),
        ("cmk_time_agent", "stack"),
        ("cmk_time_snmp", "stack"),
        ("cmk_time_ds", "stack"),
        ("execution_time", "line"),
    ],
    "optional_metrics": ["cmk_time_agent", "cmk_time_snmp", "cmk_time_ds"],
}

graph_info["cpu_time"] = {
    "title": _("CPU Time"),
    "metrics": [
        ("user_time", "area"),
        ("system_time", "stack"),
        ("user_time,system_time,+", "line", _("Total")),
    ],
    "conflicting_metrics": ["children_user_time"],
}

graph_info["tapes_utilization"] = {
    "title": _("Tapes utilization"),
    "metrics": [
        ("tapes_free", "area"),
        ("tapes_total", "line"),
    ],
    "scalars": [
        "tapes_free:warn",
        "tapes_free:crit",
    ]
}

graph_info["storage_processor_utilization"] = {
    "title": _("Storage Processor utilization"),
    "metrics": [("storage_processor_util", "area"),],
    "scalars": [
        "storage_processor_util:warn",
        "storage_processor_util:crit",
    ]
}

graph_info["cpu_load"] = {
    "title": _("CPU Load - %(load1:max@count) CPU Cores"),
    "metrics": [
        ("load1", "area"),
        ("load5", "line"),
        ("load15", "line"),
    ],
    "scalars": [
        "load1:warn",
        "load1:crit",
    ],
    "optional_metrics": [
        "load5",
        "load15",
    ],
}

graph_info["fgpa_utilization"] = {
    "title": _("FGPA utilization"),
    "metrics": [("fpga_util", "area"),],
    "scalars": [
        "fpga_util:warn",
        "fpga_util:crit",
    ],
    "range": (0, 100),
}

#
# CPU UTILIZATION
#

graph_info["util_average_1"] = {
    "metrics": [
        ("util", "area"),
        ("util_average", "line"),
    ],
    "scalars": [
        "util:warn",
        "util:crit",
    ],
    "range": ("util:min", "util:max"),
}

graph_info["util_average_2"] = {
    "title": _("CPU utilization"),
    "metrics": [("util1", "area"), ("util15", "line")],
    "scalars": [
        "util1:warn",
        "util1:crit",
    ],
    "range": (0, 100),
}

graph_info["cpu_utilization_numcpus"] = {
    "title": _("CPU utilization (%(util_numcpu_as_max:max@count) CPU Threads)"),
    "metrics": [
        ("user", "area"),
        ("util_numcpu_as_max,user,-#ff6000", "stack", _("Privileged")),
        ("util_numcpu_as_max#004080", "line", _("Total")),
    ],
    "scalars": [
        "util_numcpu_as_max:warn",
        "util_numcpu_as_max:crit",
    ],
    "range": (0, 100),
    "optional_metrics": ["user"],
}

graph_info["cpu_utilization_simple"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("util#004080", "line", _("Total")),
    ],
    "conflicting_metrics": [
        "idle",
        "cpu_util_guest",
        "cpu_util_steal",
        "io_wait",
    ],
    "range": (0, 100),
}

#TODO which warn,crit?
graph_info["cpu_utilization_3"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("idle", "stack"),
        ("nice", "stack"),
    ],
    "range": (0, 100),
}

#TODO which warn,crit?
graph_info["cpu_utilization_4"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("idle", "stack"),
        ("io_wait", "stack"),
    ],
    "range": (0, 100),
}

# The following 6 graphs come in pairs.
# If possible, we display the "util" metric,
# otherwise we display the sum of the present metrics.

#TODO which warn,crit?
graph_info["cpu_utilization_5"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("user,system,io_wait,+,+#004080", "line", _("Total")),
    ],
    "conflicting_metrics": [
        "util",
        "idle",
        "cpu_util_guest",
        "cpu_util_steal",
    ],
    "range": (0, 100),
}

graph_info["cpu_utilization_5_util"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("util#004080", "line", _("Total")),
    ],
    "scalars": [
        "util:warn",
        "util:crit",
    ],
    "conflicting_metrics": [
        "cpu_util_guest",
        "cpu_util_steal",
    ],
    "range": (0, 100),
}

#TODO which warn,crit?
graph_info["cpu_utilization_6"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("cpu_util_steal", "stack"),
        ("user,system,io_wait,cpu_util_steal,+,+,+#004080", "line", _("Total")),
    ],
    "conflicting_metrics": [
        "util",
        "cpu_util_guest",
    ],
    "omit_zero_metrics": True,
    "range": (0, 100),
}

graph_info["cpu_utilization_6_util"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("cpu_util_steal", "stack"),
        ("util#004080", "line", _("Total")),
    ],
    "scalars": [
        "util:warn",
        "util:crit",
    ],
    "conflicting_metrics": ["cpu_util_guest",],
    "omit_zero_metrics": True,
    "range": (0, 100),
}

#TODO which warn,crit?
graph_info["cpu_utilization_7"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("cpu_util_guest", "stack"),
        ("cpu_util_steal", "stack"),
        ("user,system,io_wait,cpu_util_guest,cpu_util_steal,+,+,+,+#004080", "line", _("Total")),
    ],
    "conflicting_metrics": ["util",],
    "omit_zero_metrics": True,
    "range": (0, 100),
}

graph_info["cpu_utilization_7_util"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("io_wait", "stack"),
        ("cpu_util_guest", "stack"),
        ("cpu_util_steal", "stack"),
        ("util#004080", "line", _("Total")),
    ],
    "scalars": [
        "util:warn",
        "util:crit",
    ],
    "omit_zero_metrics": True,
    "range": (0, 100),
}

# ^-- last six graphs go pairwise together (see above)

#TODO which warn,crit?
graph_info["cpu_utilization_8"] = {
    "title": _("CPU utilization"),
    "metrics": [
        ("user", "area"),
        ("system", "stack"),
        ("interrupt", "stack"),
    ],
    "range": (0, 100),
}

graph_info["util_fallback"] = {
    "metrics": [("util", "area"),],
    "scalars": [
        "util:warn",
        "util:crit",
    ],
    "range": ("util:min", "util:max"),
    "conflicting_metrics": [
        "util_average",
        "system",
    ],
}

graph_info["cpu_entitlement"] = {
    "title": _("CPU entitlement"),
    "metrics": [("cpu_entitlement", "area"), ("cpu_entitlement_util", "line")],
}

graph_info["per_core_utilization"] = {
    "title": _("Per Core utilization"),
    "metrics": [("cpu_core_util_%d" % num, "line") for num in range(MAX_CORES)],
    "range": (0, 100),
    "optional_metrics": ["cpu_core_util_%d" % num for num in range(2, MAX_CORES)]
}

graph_info["fs_used"] = {
    "metrics": [
        ("fs_used", "area"),
        ("fs_size,fs_used,-#e3fff9", "stack", _("Free space")),
        ("fs_size", "line"),
    ],
    "scalars": [
        "fs_used:warn",
        "fs_used:crit",
    ],
    "range": (0, "fs_used:max"),
    "conflicting_metrics": ["fs_free"],
}

# draw a different graph if space reserved for root was excluded
graph_info["fs_used_2"] = {
    "metrics": [
        ("fs_used", "area"),
        ("fs_free", "stack"),
        ("reserved", "stack"),
        ("fs_size", "line"),
    ],
    "scalars": [
        "fs_used:warn",
        "fs_used:crit",
    ],
    "range": (0, "fs_used:max"),
}

graph_info["growing"] = {
    "title": _("Growing"),
    "metrics": [(
        "fs_growth.max,0,MAX",
        "area",
        _("Growth"),
    ),],
}

graph_info["shrinking"] = {
    "title": _("Shrinking"),
    "consolidation_function": "min",
    "metrics": [("fs_growth.min,0,MIN,-1,*#299dcf", "-area", _("Shrinkage")),],
}

graph_info["fs_trend"] = {
    "metrics": [("fs_trend", "line"),],
}

graph_info["wasted_space_of_tables_and_indexes"] = {
    "title": _("Wasted space of tables and indexes"),
    "metrics": [
        ("tablespace_wasted", "area"),
        ("indexspace_wasted", "stack"),
    ],
    "legend_scale": MB,
    "legend_precision": 2,
}

graph_info["firewall_connections"] = {
    "title": _("Firewall connections"),
    "metrics": [
        ("fw_connections_active", "stack"),
        ("fw_connections_established", "stack"),
        ("fw_connections_halfopened", "stack"),
        ("fw_connections_halfclosed", "stack"),
        ("fw_connections_passthrough", "stack"),
    ],
}

graph_info["time_to_connect"] = {
    "title": _("Time to connect"),
    "metrics": [("connection_time", "area"),],
    "legend_scale": m,
}

graph_info["number_of_total_and_running_sessions"] = {
    "title": _("Number of total and running sessions"),
    "metrics": [
        ("running_sessions", "line"),
        ("total_sessions", "line"),
    ],
    "legend_precision": 0
}

graph_info["number_of_shared_and_exclusive_locks"] = {
    "title": _("Number of shared and exclusive locks"),
    "metrics": [
        ("shared_locks", "area"),
        ("exclusive_locks", "stack"),
    ],
    "legend_precision": 0
}

# diskstat checks

graph_info["disk_utilization"] = {
    "metrics": [("disk_utilization", "area"),],
    "range": (0, 100),
    "scalars": [
        "disk_utilization:warn",
        "disk_utilization:crit",
    ],
}

graph_info["disk_throughput"] = {
    "title": _("Disk throughput"),
    "metrics": [
        ("disk_read_throughput", "area"),
        ("disk_write_throughput", "-area"),
    ],
    "scalars": [
        ("disk_read_throughput:warn", "Warning read"),
        ("disk_read_throughput:crit", "Critical read"),
        ("disk_write_throughput:warn,-1,*", "Warning write"),
        ("disk_write_throughput:crit,-1,*", "Critical write"),
    ],
    "legend_scale": MB,
}

graph_info["disk_io_operations"] = {
    "title": _("Disk I/O operations"),
    "metrics": [
        ("disk_read_ios", "area"),
        ("disk_write_ios", "-area"),
    ],
}

graph_info["direct_and_buffered_io_operations"] = {
    "title": _("Direct and buffered I/O operations"),
    "metrics": [
        ("direct_io", "stack"),
        ("buffered_io", "stack"),
    ],
}

graph_info["average_request_size"] = {
    "title": _("Average request size"),
    "metrics": [
        ("disk_average_read_request_size", "area"),
        ("disk_average_write_request_size", "-area"),
    ],
    "legend_scale": KB,
}

graph_info["average_end_to_end_wait_time"] = {
    "title": _("Average end to end wait time"),
    "metrics": [
        ("disk_average_read_wait", "area"),
        ("disk_average_write_wait", "-area"),
    ],
}

graph_info["spare_and_broken_disks"] = {
    "title": _("Spare and broken disks"),
    "metrics": [
        ("disks", "area"),
        ("spare_disks", "stack"),
        ("failed_disks", "stack"),
    ],
}

graph_info["database_sizes"] = {
    "title": _("Database sizes"),
    "metrics": [
        ("database_size", "area"),
        ("unallocated_size", "stack"),
        ("reserved_size", "stack"),
        ("data_size", "stack"),
        ("indexes_size", "stack"),
        ("unused_size", "stack"),
        ("database_reclaimable", "stack"),
    ],
    "optional_metrics": [
        "unallocated_size",
        "reserved_size",
        "data_size",
        "indexes_size",
        "unused_size",
        "database_reclaimable",
    ],
    "legend_scale": MB,
}

# TODO: Warum ist hier überall line? Default ist Area.
# Kann man die hit ratios nicht schön stacken? Ist
# nicht total die Summe der anderen?

graph_info["bufferpool_hitratios"] = {
    "title": _("Bufferpool Hitratios"),
    "metrics": [
        ("total_hitratio", "line"),
        ("data_hitratio", "line"),
        ("index_hitratio", "line"),
        ("xda_hitratio", "line"),
    ],
}

graph_info["deadlocks_and_waits"] = {
    "metrics": [
        ("deadlocks", "area"),
        ("lockwaits", "stack"),
    ],
}

graph_info["tablespace_sizes"] = {
    "title": _("Tablespace sizes"),
    "metrics": [
        ("tablespace_size", "area"),
        ("tablespace_used", "area"),
    ],
    "scalars": [
        "tablespace_size:warn",
        "tablespace_size:crit",
    ],
    "range": (0, "tablespace_max_size"),
}

# Printer

graph_info["printer_queue"] = {
    "metrics": [("printer_queue", "area")],
    "range": (0, 10),
}

graph_info["supply_toner_cyan"] = {
    "metrics": [("supply_toner_cyan", "area")],
    "range": (0, 100),
}

graph_info["supply_toner_magenta"] = {
    "metrics": [("supply_toner_magenta", "area")],
    "range": (0, 100),
}

graph_info["supply_toner_yellow"] = {
    "metrics": [("supply_toner_yellow", "area")],
    "range": (0, 100),
}

graph_info["supply_toner_black"] = {
    "metrics": [("supply_toner_black", "area")],
    "range": (0, 100),
}

graph_info["supply_toner_other"] = {
    "metrics": [("supply_toner_other", "area")],
    "range": (0, 100),
}

graph_info["printed_pages"] = {
    "title": _("Printed pages"),
    "metrics": [
        ("pages_color_a4", "stack"),
        ("pages_color_a3", "stack"),
        ("pages_bw_a4", "stack"),
        ("pages_bw_a3", "stack"),
        ("pages_color", "stack"),
        ("pages_bw", "stack"),
        ("pages_total", "line"),
    ],
    "optional_metrics": [
        "pages_color_a4",
        "pages_color_a3",
        "pages_bw_a4",
        "pages_bw_a3",
        "pages_color",
        "pages_bw",
    ],
    "range": (0, "pages_total:max"),
}

# Networking

graph_info["bandwidth_translated"] = {
    "title": _("Bandwidth"),
    "metrics": [
        ("if_in_octets,8,*@bits/s", "area", _("Input bandwidth")),
        ("if_out_octets,8,*@bits/s", "-area", _("Output bandwidth")),
    ],
    "scalars": [
        ("if_in_octets:warn", _("Warning (In)")),
        ("if_in_octets:crit", _("Critical (In)")),
        ("if_out_octets:warn,-1,*", _("Warning (Out)")),
        ("if_out_octets:crit,-1,*", _("Critical (Out)")),
    ],
}

# Same but for checks that have been translated in to bits/s
graph_info["bandwidth"] = {
    "title": _("Bandwidth"),
    "metrics": [
        (
            "if_in_bps",
            "area",
        ),
        (
            "if_out_bps",
            "-area",
        ),
    ],
    "scalars": [
        ("if_in_bps:warn", _("Warning (In)")),
        ("if_in_bps:crit", _("Critical (In)")),
        ("if_out_bps:warn,-1,*", _("Warning (Out)")),
        ("if_out_bps:crit,-1,*", _("Critical (Out)")),
    ],
}

graph_info["packets_2"] = {
    "title": _("Packets"),
    "metrics": [
        ("if_in_pkts", "area"),
        ("if_out_non_unicast", "-area"),
        ("if_out_unicast", "-stack"),
    ],
}

graph_info["packets_3"] = {
    "title": _("Packets"),
    "metrics": [
        ("if_in_pkts", "area"),
        ("if_out_pkts", "-area"),
    ],
}

graph_info["traffic"] = {
    "title": _("Traffic"),
    "metrics": [
        ("if_in_octets", "area"),
        ("if_out_non_unicast_octets", "-area"),
        ("if_out_unicast_octets", "-stack"),
    ],
}

graph_info["wlan_errors"] = {
    "title": _("WLAN errors, reset operations and transmission retries"),
    "metrics": [
        ("wlan_physical_errors", "area"),
        ("wlan_resets", "stack"),
        ("wlan_retries", "stack"),
    ],
}

# TODO: show this graph instead of Bandwidth if this is configured
# in the check's parameters. But is this really a good solution?
# We could use a condition on if_in_octets:min. But if this value
# is missing then evaluating the condition will fail. Solution
# could be using 0 for bits and 1 for octets and making sure that
# this value is not used anywhere.
# graph_info["octets"] = {
#     "title" : _("Octets"),
#     "metrics" : [
#         ( "if_in_octets",      "area" ),
#         ( "if_out_octets",     "-area" ),
#     ],
# }

graph_info["packets_1"] = {
    "title": _("Packets"),
    "metrics": [
        ("if_in_unicast", "area"),
        ("if_in_non_unicast", "stack"),
        ("if_out_unicast", "-area"),
        ("if_out_non_unicast", "-stack"),
    ],
}

graph_info["if_errors"] = {
    "title": _("Errors"),
    "metrics": [
        ("if_in_errors", "area"),
        ("if_in_discards", "stack"),
        ("if_out_errors", "-area"),
        ("if_out_discards", "-stack"),
    ],
}

graph_info["ram_swap_used"] = {
    "title": _("RAM + Swap used"),
    "metrics": [
        ("mem_used", "area"),
        ("swap_used", "stack"),
    ],
    "conflicting_metrics": ["swap_total"],
    "scalars": [
        ("swap_used:max,mem_used:max,+#008080", _("Total RAM + Swap installed")),
        ("mem_used:max#80ffff", _("Total RAM installed")),
    ],
    "range": (0, "swap_used:max,mem_used:max,+"),
}

graph_info["mem_used_percent"] = {
    "metrics": [("mem_used_percent", "area"),],
    "scalars": [
        "mem_used_percent:warn",
        "mem_used_percent:crit",
    ],
    "range": (0, 100),
}

graph_info["cpu_mem_used_percent"] = {
    "metrics": [("cpu_mem_used_percent", "area"),],
    "scalars": ["cpu_mem_used_percent:warn", "cpu_mem_used_percent:crit"],
    "range": (0, 100),
}

graph_info["mem_trend"] = {
    "metrics": [("mem_trend", "line"),],
}

graph_info["mem_growing"] = {
    "title": _("Growing"),
    "metrics": [(
        "mem_growth.max,0,MAX",
        "area",
        _("Growth"),
    ),],
}

graph_info["mem_shrinking"] = {
    "title": _("Shrinking"),
    "consolidation_function": "min",
    "metrics": [("mem_growth.min,0,MIN,-1,*#299dcf", "-area", _("Shrinkage")),],
}

# Linux memory graphs. They are a lot...

graph_info["ram_swap_overview"] = {
    "title": _("RAM + Swap overview"),
    "metrics": [
        ("mem_total", "area"),
        ("swap_total", "stack"),
        ("mem_used", "area"),
        ("swap_used", "stack"),
    ],
}

graph_info["swap"] = {
    "title": _("Swap"),
    "metrics": [
        ("swap_total", "area"),
        ("swap_used", "area"),
        ("swap_cached", "stack"),
    ],
}

graph_info["caches"] = {
    "title": _("Caches"),
    "metrics": [
        ("mem_lnx_slab", "stack"),
        ("swap_cached", "stack"),
        ("mem_lnx_buffers", "stack"),
        ("mem_lnx_cached", "stack"),
    ],
}

graph_info["active_and_inactive_memory_anon"] = {
    "title": _("Active and Inactive Memory"),
    "metrics": [
        ("mem_lnx_inactive_anon", "stack"),
        ("mem_lnx_inactive_file", "stack"),
        ("mem_lnx_active_anon", "stack"),
        ("mem_lnx_active_file", "stack"),
    ],
}

# TODO: Show this graph only, if the previous graph
# is not possible. This cannot be done with a condition,
# since we currently cannot state a condition on non-existing
# metrics.
graph_info["active_and_inactive_memory"] = {
    "title": _("Active and Inactive Memory"),
    "metrics": [
        ("mem_lnx_active", "area"),
        ("mem_lnx_inactive", "area"),
    ],
    "conflicting_metrics": ["mem_lnx_active_anon"],
}

graph_info["ram_used"] = {
    "title": _("RAM used"),
    "metrics": [("mem_used", "area"),],
    "conflicting_metrics": ["swap_used"],
    "scalars": [
        ("mem_used:max#000000", "Maximum"),
        ("mem_used:warn", "Warning"),
        ("mem_used:crit", "Critical"),
    ],
    "range": (0, "mem_used:max"),
}

graph_info["commit_charge"] = {
    "title": _("Commit Charge"),
    "metrics": [("pagefile_used", "area"),],
    "scalars": [
        ("pagefile_used:max#000000", "Maximum"),
        ("pagefile_used:warn", "Warning"),
        ("pagefile_used:crit", "Critical"),
    ],
    "range": (0, "pagefile_used:max"),
}

graph_info["filesystem_writeback"] = {
    "title": _("Filesystem Writeback"),
    "metrics": [
        ("mem_lnx_dirty", "area"),
        ("mem_lnx_writeback", "stack"),
        ("mem_lnx_nfs_unstable", "stack"),
        ("mem_lnx_bounce", "stack"),
        ("mem_lnx_writeback_tmp", "stack"),
    ],
}

graph_info["memory_committing"] = {
    "title": _("Memory committing"),
    "metrics": [
        ("mem_lnx_total_total", "area"),
        ("mem_lnx_committed_as", "area"),
        ("mem_lnx_commit_limit", "stack"),
    ],
}

graph_info["memory_that_cannot_be_swapped_out"] = {
    "title": _("Memory that cannot be swapped out"),
    "metrics": [
        ("mem_lnx_kernel_stack", "area"),
        ("mem_lnx_page_tables", "stack"),
        ("mem_lnx_mlocked", "stack"),
    ],
}

graph_info["huge_pages"] = {
    "title": _("Huge Pages"),
    "metrics": [
        ("mem_lnx_huge_pages_total", "area"),
        ("mem_lnx_huge_pages_free", "area"),
        ("mem_lnx_huge_pages_rsvd", "area"),
        ("mem_lnx_huge_pages_surp", "line"),
    ],
}

graph_info["vmalloc_address_space_1"] = {
    "title": _("VMalloc Address Space"),
    "metrics": [
        ("mem_lnx_vmalloc_total", "area"),
        ("mem_lnx_vmalloc_used", "area"),
        ("mem_lnx_vmalloc_chunk", "stack"),
    ],
}

# TODO: Warum ohne total? Dürfte eigentlich nicht
# vorkommen.
graph_info["vmalloc_address_space_2"] = {
    "title": _("VMalloc Address Space"),
    "metrics": [
        ("mem_lnx_vmalloc_used", "area"),
        ("mem_lnx_vmalloc_chunk", "stack"),
    ],
}

graph_info["heap_and_non_heap_memory"] = {
    "title": _("Heap and non-heap memory"),
    "metrics": [
        ("mem_heap", "area"),
        ("mem_nonheap", "stack"),
    ],
    "conflicting_metrics": [
        "mem_heap_committed",
        "mem_nonheap_committed",
    ],
}

graph_info["heap_memory_usage"] = {
    "title": _("Heap memory usage"),
    "metrics": [
        ("mem_heap_committed", "area"),
        ("mem_heap", "area"),
    ],
    "scalars": [
        "mem_heap:warn",
        "mem_heap:crit",
    ]
}

graph_info["non-heap_memory_usage"] = {
    "title": _("Non-heap memory usage"),
    "metrics": [
        ("mem_nonheap_committed", "area"),
        ("mem_nonheap", "area"),
    ],
    "scalars": [
        "mem_nonheap:warn",
        "mem_nonheap:crit",
        "mem_nonheap:max",
    ]
}

graph_info["private_and_shared_memory"] = {
    "title": _("Private and shared memory"),
    "metrics": [
        ("mem_esx_shared", "area"),
        ("mem_esx_private", "area"),
    ],
}

graph_info["tcp_connection_states"] = {
    "title": _("TCP Connection States"),
    "metrics": [
        ("tcp_listen", "stack"),
        ("tcp_syn_sent", "stack"),
        ("tcp_syn_recv", "stack"),
        ("tcp_established", "stack"),
        ("tcp_time_wait", "stack"),
        ("tcp_last_ack", "stack"),
        ("tcp_close_wait", "stack"),
        ("tcp_closed", "stack"),
        ("tcp_closing", "stack"),
        ("tcp_fin_wait1", "stack"),
        ("tcp_fin_wait2", "stack"),
        ("tcp_bound", "stack"),
        ("tcp_idle", "stack"),
    ],
    "omit_zero_metrics": True,
    "optional_metrics": ["tcp_bound", "tcp_idle"]
}

graph_info["cluster_hosts"] = {
    "title": _("Hosts"),
    "metrics": [
        ("hosts_active", "stack"),
        ("hosts_inactive", "stack"),
        ("hosts_degraded", "stack"),
        ("hosts_offline", "stack"),
        ("hosts_other", "stack"),
    ],
    "optional_metrics": ["hosts_active"],
}

graph_info["host_and_service_checks"] = {
    "title": _("Host and Service Checks"),
    "metrics": [
        ("host_check_rate", "stack"),
        ("service_check_rate", "stack"),
    ],
}

graph_info["number_of_monitored_hosts_and_services"] = {
    "title": _("Number of Monitored Hosts and Services"),
    "metrics": [
        ("monitored_hosts", "stack"),
        ("monitored_services", "stack"),
    ],
}

graph_info["livestatus_connects_and_requests"] = {
    "title": _("Livestatus Connects and Requests"),
    "metrics": [
        ("livestatus_request_rate", "area"),
        ("livestatus_connect_rate", "area"),
    ],
}

graph_info["message_processing"] = {
    "title": _("Message processing"),
    "metrics": [
        ("average_message_rate", "area"),
        ("average_drop_rate", "area"),
    ],
}

graph_info["rule_efficiency"] = {
    "title": _("Rule efficiency"),
    "metrics": [
        ("average_rule_trie_rate", "area"),
        ("average_rule_hit_rate", "area"),
    ],
}

graph_info["livestatus_requests_per_connection"] = {
    "title": _("Livestatus Requests per Connection"),
    "metrics": [("livestatus_request_rate,livestatus_connect_rate,/#88aa33", "area",
                 _("Average requests per connection")),],
}

graph_info["livestatus_usage"] = {
    "metrics": [("livestatus_usage", "area"),],
    "range": (0, 100),
}

graph_info["helper_usage_cmk"] = {
    "metrics": [("helper_usage_cmk", "area"),],
    "range": (0, 100),
}

graph_info["helper_usage_generic"] = {
    "metrics": [("helper_usage_generic", "area"),],
    "range": (0, 100),
}

graph_info["average_check_latency"] = {
    "title": _("Average check latency"),
    "metrics": [
        ("average_latency_cmk", "line"),
        ("average_latency_generic", "line"),
    ],
}

graph_info["pending_updates"] = {
    "title": _("Pending updates"),
    "metrics": [
        ("normal_updates", "stack"),
        ("security_updates", "stack"),
    ],
}

graph_info["handled_requests"] = {
    "title": _("Handled Requests"),
    "metrics": [
        ("requests_cmk_views", "stack"),
        ("requests_cmk_wato", "stack"),
        ("requests_cmk_bi", "stack"),
        ("requests_cmk_snapins", "stack"),
        ("requests_cmk_dashboards", "stack"),
        ("requests_cmk_other", "stack"),
        ("requests_nagvis_snapin", "stack"),
        ("requests_nagvis_ajax", "stack"),
        ("requests_nagvis_other", "stack"),
        ("requests_images", "stack"),
        ("requests_styles", "stack"),
        ("requests_scripts", "stack"),
        ("requests_other", "stack"),
    ],
    "omit_zero_metrics": True,
}

graph_info["cmk_http_pagetimes"] = {
    "title": _("Time spent for various page types"),
    "metrics": [
        ("secs_cmk_views", "stack"),
        ("secs_cmk_wato", "stack"),
        ("secs_cmk_bi", "stack"),
        ("secs_cmk_snapins", "stack"),
        ("secs_cmk_dashboards", "stack"),
        ("secs_cmk_other", "stack"),
        ("secs_nagvis_snapin", "stack"),
        ("secs_nagvis_ajax", "stack"),
        ("secs_nagvis_other", "stack"),
        ("secs_images", "stack"),
        ("secs_styles", "stack"),
        ("secs_scripts", "stack"),
        ("secs_other", "stack"),
    ],
    "omit_zero_metrics": True,
}

graph_info["cmk_http_traffic"] = {
    "title": _("Bytes sent"),
    "metrics": [
        ("bytes_cmk_views", "stack"),
        ("bytes_cmk_wato", "stack"),
        ("bytes_cmk_bi", "stack"),
        ("bytes_cmk_snapins", "stack"),
        ("bytes_cmk_dashboards", "stack"),
        ("bytes_cmk_other", "stack"),
        ("bytes_nagvis_snapin", "stack"),
        ("bytes_nagvis_ajax", "stack"),
        ("bytes_nagvis_other", "stack"),
        ("bytes_images", "stack"),
        ("bytes_styles", "stack"),
        ("bytes_scripts", "stack"),
        ("bytes_other", "stack"),
    ],
    "omit_zero_metrics": True,
}

graph_info["amount_of_mails_in_queues"] = {
    "title": _("Amount of mails in queues"),
    "metrics": [
        ("mail_queue_deferred_length", "stack"),
        ("mail_queue_active_length", "stack"),
    ],
}

graph_info["size_of_mails_in_queues"] = {
    "title": _("Size of mails in queues"),
    "metrics": [
        ("mail_queue_deferred_size", "stack"),
        ("mail_queue_active_size", "stack"),
    ],
}

graph_info["inbound_and_outbound_messages"] = {
    "title": _("Inbound and Outbound Messages"),
    "metrics": [
        ("messages_outbound", "stack"),
        ("messages_inbound", "stack"),
    ],
}

graph_info["modems"] = {
    "title": _("Modems"),
    "metrics": [
        ("active_modems", "area"),
        ("registered_modems", "line"),
        ("total_modems", "line"),
    ],
}

graph_info["net_data_traffic"] = {
    "title": _("Net data traffic"),
    "metrics": [
        ("net_data_recv", "stack"),
        ("net_data_sent", "stack"),
    ],
}

# For the 'ps' check there are multiple graphs.
# Without the graph info 'number_of_processes', the graph will not show,
# because 'size_per_process' uses the variable name 'processes' as well.
# Once a variable is used by some other graph it will not create a single graph anymore.
# That is why we have to define a specific graph info here.
# Further details see here: metrics/utils.py -> _get_implicit_graph_templates()
graph_info["number_of_processes"] = {
    "title": _("Number of processes"),
    "metrics": [("processes", "area"),]
}

graph_info["size_of_processes"] = {
    "title": _("Size of processes"),
    "metrics": [
        ("process_resident_size", "area"),
        ("process_virtual_size", "stack"),
        ("process_mapped_size", "stack"),
    ],
    "optional_metrics": ["process_mapped_size"]
}

graph_info["size_per_process"] = {
    "title": _("Size per process"),
    "metrics": [
        ("process_resident_size,processes,/", "area", _("Average resident size per process")),
        ("process_virtual_size,processes,/", "stack", _("Average virtual size per process")),
    ]
}

graph_info["throughput"] = {
    "title": _("Throughput"),
    "metrics": [
        ("fc_tx_bytes", "-area"),
        ("fc_rx_bytes", "area"),
    ],
}

graph_info["frames"] = {
    "title": _("Frames"),
    "metrics": [
        ("fc_tx_frames", "-area"),
        ("fc_rx_frames", "area"),
    ],
}

graph_info["words"] = {
    "title": _("Words"),
    "metrics": [
        ("fc_tx_words", "-area"),
        ("fc_rx_words", "area"),
    ],
}

graph_info["fc_errors"] = {
    "title": _("Errors"),
    "metrics": [
        ("fc_crc_errors", "area"),
        ("fc_c3discards", "stack"),
        ("fc_notxcredits", "stack"),
        ("fc_encouts", "stack"),
        ("fc_encins", "stack"),
        ("fc_bbcredit_zero", "stack"),
    ],
    "optional_metrics": [
        "fc_encins",
        "fc_bbcredit_zero",
    ],
}

graph_info["fc_errors_detailed"] = {
    "title": _("Errors"),
    "metrics": [
        ("fc_link_fails", "stack"),
        ("fc_sync_losses", "stack"),
        ("fc_prim_seq_errors", "stack"),
        ("fc_invalid_tx_words", "stack"),
        ("fc_invalid_crcs", "stack"),
        ("fc_address_id_errors", "stack"),
        ("fc_link_resets_in", "stack"),
        ("fc_link_resets_out", "stack"),
        ("fc_offline_seqs_in", "stack"),
        ("fc_offline_seqs_out", "stack"),
        ("fc_c2c3_discards", "stack"),
        ("fc_c2_fbsy_frames", "stack"),
        ("fc_c2_frjt_frames", "stack"),
    ]
}


def register_netapp_api_vs_traffic_graphs():
    for what, text in [
        ("nfs", "NFS"),
        ("cifs", "CIFS"),
        ("san", "SAN"),
        ("fcp", "FCP"),
        ("iscsi", "iSCSI"),
        ("nfsv4", "NFSv4"),
        ("nfsv4_1", "NFSv4.1"),
    ]:
        graph_info["%s_traffic" % what] = {
            "title": _("%s traffic") % text,
            "metrics": [
                ("%s_read_data" % what, "-area"),
                ("%s_write_data" % what, "area"),
            ],
        }

        graph_info["%s_latency" % what] = {
            "title": _("%s latency") % text,
            "metrics": [
                ("%s_read_latency" % what, "-area"),
                ("%s_write_latency" % what, "area"),
            ],
        }

        graph_info["%s_ops" % what] = {
            "title": _("%s operations") % text,
            "metrics": [
                ("%s_read_ops" % what, "-area"),
                ("%s_write_ops" % what, "area"),
            ],
        }


register_netapp_api_vs_traffic_graphs()

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

graph_info["access_point_statistics"] = {
    "title": _("Access point statistics"),
    "metrics": [
        ("ap_devices_total", "area"),
        ("ap_devices_drifted", "area"),
        ("ap_devices_not_responding", "stack"),
    ]
}

graph_info["round_trip_average"] = {
    "title": _("Round trip average"),
    "metrics": [
        ("rtmax", "area"),
        ("rtmin", "area"),
        ("rta", "line"),
    ],
    "scalars": [
        "rta:warn",
        "rta:crit",
    ]
}

graph_info["packet_loss"] = {
    "title": _("Packet loss"),
    "metrics": [("pl", "area"),],
    "scalars": [
        "pl:warn",
        "pl:crit",
    ]
}


def register_hop_graphs():
    for idx in range(1, MAX_NUMBER_HOPS):
        graph_info["hop_%d_round_trip_average" % idx] = {
            "title": _("Hop %d Round trip average") % idx,
            "metrics": [
                ("hop_%d_rtmax" % idx, "area"),
                ("hop_%d_rtmin" % idx, "area"),
                ("hop_%d_rta" % idx, "line"),
                ("hop_%d_rtstddev" % idx, "line"),
            ],
        }
        graph_info["hop_%d_packet_loss" % idx] = {
            "title": _("Hop %d Packet loss") % idx,
            "metrics": [("hop_%d_pl" % idx, "area"),],
        }


register_hop_graphs()


def register_hop_response_graph():
    new_graph = {
        "title": _("Hop response times"),
        "metrics": [],
        "optional_metrics": [],
    }  # type: Dict[str, Any]
    for idx in range(1, MAX_NUMBER_HOPS):
        color = indexed_color(idx, MAX_NUMBER_HOPS)
        new_graph["metrics"].append(
            ("hop_%d_response_time%s" % (idx, parse_color_into_hexrgb(color)), "line"))
        if idx > 0:
            new_graph["optional_metrics"].append(("hop_%d_response_time" % (idx + 1)))

    graph_info["hop_response_time"] = new_graph


register_hop_response_graph()

graph_info["mem_perm_used"] = {
    "metrics": [("mem_perm_used", "area")],
    "scalars": [
        "mem_perm_used:warn",
        "mem_perm_used:crit",
        ("mem_perm_used:max#000000", _("Max Perm used")),
    ],
    "range": (0, "mem_perm_used:max")
}

graph_info["palo_alto_sessions"] = {
    "title": _("Palo Alto Sessions"),
    "metrics": [
        ("tcp_active_sessions", "area"),
        ("udp_active_sessions", "stack"),
        ("icmp_active_sessions", "stack"),
        ("sslproxy_active_sessions", "stack"),
    ],
}

graph_info["varnish_backend_connections"] = {
    "title": _("Varnish Backend Connections"),
    "metrics": [
        ("varnish_backend_busy_rate", "line"),
        ("varnish_backend_unhealthy_rate", "line"),
        ("varnish_backend_req_rate", "line"),
        ("varnish_backend_recycle_rate", "line"),
        ("varnish_backend_retry_rate", "line"),
        ("varnish_backend_fail_rate", "line"),
        ("varnish_backend_toolate_rate", "line"),
        ("varnish_backend_conn_rate", "line"),
        ("varnish_backend_reuse_rate", "line"),
    ],
}

graph_info["varnish_cache"] = {
    "title": _("Varnish Cache"),
    "metrics": [
        ("varnish_cache_miss_rate", "line"),
        ("varnish_cache_hit_rate", "line"),
        ("varnish_cache_hitpass_rate", "line"),
    ],
}

graph_info["varnish_clients"] = {
    "title": _("Varnish Clients"),
    "metrics": [
        ("varnish_client_req_rate", "line"),
        ("varnish_client_conn_rate", "line"),
        ("varnish_client_drop_rate", "line"),
        ("varnish_client_drop_late_rate", "line"),
    ],
}

graph_info["varnish_esi_errors_and_warnings"] = {
    "title": _("Varnish ESI Errors and Warnings"),
    "metrics": [
        ("varnish_esi_errors_rate", "line"),
        ("varnish_esi_warnings_rate", "line"),
    ],
}

graph_info["varnish_fetch"] = {
    "title": _("Varnish Fetch"),
    "metrics": [
        ("varnish_fetch_oldhttp_rate", "line"),
        ("varnish_fetch_head_rate", "line"),
        ("varnish_fetch_eof_rate", "line"),
        ("varnish_fetch_zero_rate", "line"),
        ("varnish_fetch_304_rate", "line"),
        ("varnish_fetch_length_rate", "line"),
        ("varnish_fetch_failed_rate", "line"),
        ("varnish_fetch_bad_rate", "line"),
        ("varnish_fetch_close_rate", "line"),
        ("varnish_fetch_1xx_rate", "line"),
        ("varnish_fetch_chunked_rate", "line"),
        ("varnish_fetch_204_rate", "line"),
    ],
}

graph_info["varnish_objects"] = {
    "title": _("Varnish Objects"),
    "metrics": [
        ("varnish_objects_expired_rate", "line"),
        ("varnish_objects_lru_nuked_rate", "line"),
        ("varnish_objects_lru_moved_rate", "line"),
    ],
}

graph_info["varnish_worker"] = {
    "title": _("Varnish Worker"),
    "metrics": [
        ("varnish_worker_lqueue_rate", "line"),
        ("varnish_worker_create_rate", "line"),
        ("varnish_worker_drop_rate", "line"),
        ("varnish_worker_rate", "line"),
        ("varnish_worker_failed_rate", "line"),
        ("varnish_worker_queued_rate", "line"),
        ("varnish_worker_max_rate", "line"),
    ],
}

graph_info["optical_signal_power"] = {
    "title": _("Optical Signal Power"),
    "metrics": [("rx_light", "line"), ("tx_light", "line")]
}

for i in range(10):
    graph_info["optical_signal_power_lane_%d" % i] = {
        "title": _("Optical Signal Power Lane %d") % i,
        "metrics": [("rx_light_%d" % i, "line"), ("tx_light_%d" % i, "line")]
    }

graph_info["page_activity"] = {
    "title": _("Page Activity"),
    "metrics": [
        ("page_reads_sec", "area"),
        ("page_writes_sec", "-area"),
    ]
}

graph_info["datafile_sizes"] = {
    "title": _("Datafile Sizes"),
    "metrics": [("allocated_size", "line"), ("data_size", "area")]
}

graph_info["authentication_failures"] = {
    "title": _("Authentication Failures"),
    "metrics": [("udp_failed_auth", "line"), ("tcp_failed_auth", "line")]
}

graph_info["allocate_requests_exceeding_port_limit"] = {
    "title": _("Allocate Requests Exceeding Port Limit"),
    "metrics": [("udp_allocate_requests_exceeding_port_limit", "line"),
                ("tcp_allocate_requests_exceeding_port_limit", "line")]
}

graph_info["packets_dropped"] = {
    "title": _("Packets Dropped"),
    "metrics": [
        ("udp_packets_dropped", "line"),
        ("tcp_packets_dropped", "line"),
    ]
}


def get_skype_mobile_metrics():
    return [("active_sessions_%s" % device, idx == 0 and "area" or "stack")
            for idx, (device, _name, _color) in enumerate(skype_mobile_devices[::-1])]


graph_info["active_sessions"] = {
    "title": _("Active Sessions"),
    "metrics": get_skype_mobile_metrics(),
}

graph_info["streams"] = {
    "title": _("Streams"),
    "metrics": [("failed_inbound_streams", "area"), ("failed_outbound_streams", "-area")]
}

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

graph_info["dhcp_statistics_received"] = {
    "title": _("DHCP statistics (received messages)"),
    "metrics": [
        ("dhcp_discovery", "area"),
        ("dhcp_requests", "stack"),
        ("dhcp_releases", "stack"),
        ("dhcp_declines", "stack"),
        ("dhcp_informs", "stack"),
        ("dhcp_others", "stack"),
    ]
}

graph_info["dhcp_statistics_sent"] = {
    "title": _("DHCP statistics (sent messages)"),
    "metrics": [
        ("dhcp_offers", "area"),
        ("dhcp_acks", "stack"),
        ("dhcp_nacks", "stack"),
    ]
}

graph_info["dns_statistics"] = {
    "title": _("DNS statistics"),
    "metrics": [
        ("dns_successes", "area"),
        ("dns_referrals", "stack"),
        ("dns_recursion", "stack"),
        ("dns_failures", "stack"),
        ("dns_nxrrset", "stack"),
        ("dns_nxdomain", "stack"),
    ]
}

graph_info["connection_durations"] = {
    "title": _("Connection durations"),
    "metrics": [
        ("connections_duration_min", "line"),
        ("connections_duration_max", "line"),
        ("connections_duration_mean", "line"),
    ]
}

graph_info["http_timings"] = {
    "title": _("HTTP Timings"),
    "metrics": [
        ("time_connect", "area", _("Connect")),
        ("time_ssl", "stack", _("Negotiate SSL")),
        ("time_headers", "stack", _("Send request")),
        ("time_transfer", "stack", _("Receive full response")),
        ("time_firstbyte", "line", _("Receive start of response")),
        ("response_time", "line", _("Roundtrip")),
    ],
    "optional_metrics": ["time_ssl"],
}

graph_info["web_gateway_statistics"] = {
    "title": _("Web gateway statistics"),
    "metrics": [
        ("infections_rate", "stack"),
        ("connections_blocked_rate", "stack"),
    ],
}

graph_info["web_gateway_miscellaneous_statistics"] = {
    "title": _("Web gateway miscellaneous statistics"),
    "metrics": [
        ("open_network_sockets", "stack"),
        ("connections", "stack"),
    ],
}

graph_info["emcvnx_storage_pools_capacity"] = {
    "title": _("EMC VNX storage pools capacity"),
    "metrics": [
        ("emcvnx_consumed_capacity", "area"),
        ("emcvnx_avail_capacity", "stack"),
    ]
}

graph_info["emcvnx_storage_pools_movement"] = {
    "title": _("EMC VNX storage pools movement"),
    "metrics": [
        ("emcvnx_move_up", "area"),
        ("emcvnx_move_down", "stack"),
        ("emcvnx_move_within", "stack"),
    ]
}

graph_info["emcvnx_storage_pools_targeted"] = {
    "title": _("EMC VNX storage pools targeted tiers"),
    "metrics": [
        ("emcvnx_targeted_higher", "area"),
        ("emcvnx_targeted_lower", "stack"),
        ("emcvnx_targeted_within", "stack"),
    ]
}

graph_info['amount_of_mails_in_secondary_queues'] = {
    'title': _('Amount of mails in queues'),
    'metrics': [
        ('mail_queue_hold_length', 'stack'),
        ('mail_queue_incoming_length', 'stack'),
        ('mail_queue_drop_length', 'stack'),
    ],
}

graph_info['files_notification_spool'] = {
    'title': _('Amount of files in notification spool'),
    'metrics': [
        ('new_files', 'area'),
        ('deferred_files', 'area'),
        ('corrupted_files', 'area'),
    ],
    "optional_metrics": ['deferred_files', 'corrupted_files'],
}

graph_info['DB_connections'] = {
    'title': _('Parallel connections'),
    'metrics': [
        ('connections_max_used', 'area'),
        ('connections_max', 'line'),
    ],
}

graph_info['http_errors'] = {
    'title': _('HTTP Errors'),
    'metrics': [
        ('http_5xx_rate', 'area'),
        ('http_4xx_rate', 'area'),
    ],
}

graph_info['inodes_used'] = {
    'title': _('Used inodes'),
    'metrics': [('inodes_used', 'area'),],
    'scalars': [
        'inodes_used:warn',
        'inodes_used:crit',
        ('inodes_used:max', _('Maximum inodes')),
    ],
    'range': (0, 'inodes_used:max'),
}

graph_info["licenses"] = {
    "title": _("Licenses"),
    "metrics": [
        (
            "licenses_total",
            "area",
        ),
        (
            "licenses",
            "area",
        ),
    ],
}

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

graph_info["nodes_by_type"] = {
    "title": _("Running nodes by nodes type"),
    "metrics": [
        ("number_of_nodes", "area"),
        ("number_of_data_nodes", "area"),
    ],
}

graph_info["active_shards"] = {
    "title": _("Active shards"),
    "metrics": [
        ("active_shards", "area"),
        ("active_primary_shards", "area"),
    ],
}

graph_info["read_latency"] = {
    "title": _("Read latency"),
    "metrics": [
        ("nimble_read_latency_total", "area"),
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
    "title": _("Write latency"),
    "metrics": [
        ("nimble_write_latency_total", "area"),
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

graph_info["number_of_executors"] = {
    "title": _("Executors"),
    "metrics": [
        ("jenkins_num_executors", "area"),
        ("jenkins_busy_executors", "area"),
        ("jenkins_idle_executors", "area"),
    ],
}

graph_info["number_of_tasks"] = {
    "title": _("Tasks"),
    "metrics": [
        ("jenkins_stuck_tasks", "area"),
        ("jenkins_blocked_tasks", "area"),
        ("jenkins_pending_tasks", "area"),
    ],
}

graph_info["temperature"] = {
    "title": _("Temperature"),
    "metrics": [("temp", "area"),],
    "scalars": [
        "temp:warn",
        "temp:crit",
    ]
}

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

graph_info["current_users"] = {
    "title": _("Number of signed-in users"),
    "metrics": [("current_users", "area"),],
    "scalars": [
        "current_users:warn",
        "current_users:crit",
    ],
}
