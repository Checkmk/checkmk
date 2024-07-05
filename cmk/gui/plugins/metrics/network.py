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

metric_info["rtt"] = {
    "title": _("Round trip time"),
    "unit": "s",
    "color": "33/a",
}

metric_info["connection_time"] = {
    "title": _("Connection time"),
    "unit": "s",
    "color": "#94b65a",
}

metric_info["bytes_downloaded"] = {
    "title": _("Bytes downloaded"),
    "unit": "bytes",
    "color": "42/a",
}

metric_info["bytes_uploaded"] = {
    "title": _("Bytes uploaded"),
    "unit": "bytes",
    "color": "41/b",
}

metric_info["queries_per_sec"] = {
    "title": _("Queries per second"),
    "unit": "1/s",
    "color": "41/b",
}

metric_info["snat_usage"] = {
    "title": _("SNAT usage"),
    "unit": "%",
    "color": "21/a",
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

graph_info["if_errors"] = {
    "title": _("Errors"),
    "metrics": [
        ("if_in_errors", "area"),
        ("if_in_discards", "stack"),
        ("if_out_errors", "-area"),
        ("if_out_discards", "-stack"),
    ],
}

graph_info["bm_packets"] = {
    "title": _("Broadcast/Multicast"),
    "metrics": [
        ("if_in_mcast", "line"),
        ("if_in_bcast", "line"),
        ("if_out_mcast", "-line"),
        ("if_out_bcast", "-line"),
    ],
}

graph_info["packets_1"] = {
    "title": _("Packets"),
    "metrics": [
        ("if_in_unicast", "line"),
        ("if_in_non_unicast", "line"),
        ("if_out_unicast", "-line"),
        ("if_out_non_unicast", "-line"),
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

graph_info["time_to_connect"] = {
    "title": _("Time to connect"),
    "metrics": [
        ("connection_time", "area"),
    ],
}

graph_info["round_trip_average"] = {
    "title": _("Round trip average"),
    "metrics": [
        ("rtmax", "line"),
        ("rtmin", "line"),
        ("rta", "line"),
    ],
    "scalars": [
        "rta:warn",
        "rta:crit",
    ],
}

graph_info["packet_loss"] = {
    "title": _("Packet loss"),
    "metrics": [
        ("pl", "area"),
    ],
    "scalars": [
        "pl:warn",
        "pl:crit",
    ],
}

graph_info["inodes_used"] = {
    "title": _("Used inodes"),
    "metrics": [
        ("inodes_used", "area"),
    ],
    "scalars": [
        "inodes_used:warn",
        "inodes_used:crit",
        ("inodes_used:max", _("Maximum inodes")),
    ],
    "range": (0, "inodes_used:max"),
}

graph_info["nodes_by_type"] = {
    "title": _("Running nodes by nodes type"),
    "metrics": [
        ("number_of_nodes", "area"),
        ("number_of_data_nodes", "line"),
    ],
}

graph_info["data_transfer"] = {
    "title": _("Data transfer"),
    "metrics": [
        ("bytes_downloaded", "stack"),
        ("bytes_uploaded", "stack"),
    ],
}
