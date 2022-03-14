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

metric_info["if_total_bps"] = {
    "title": _("Total bandwidth (sum of in and out)"),
    "unit": "bits/s",
    "color": "#00e060",
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

metric_info["if_in_mcast"] = {
    "title": _("Input multicast packets"),
    "unit": "1/s",
    "color": "#00ffc0",
}

metric_info["if_in_bcast"] = {
    "title": _("Input broadcast packets"),
    "unit": "1/s",
    "color": "#00c080",
}

metric_info["if_out_mcast"] = {
    "title": _("Output multicast packets"),
    "unit": "1/s",
    "color": "#00c0ff",
}

metric_info["if_out_bcast"] = {
    "title": _("Output broadcast packets"),
    "unit": "1/s",
    "color": "#0080c0",
}
