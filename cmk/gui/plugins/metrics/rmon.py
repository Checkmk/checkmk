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
