#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _l
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

metric_info["apache_state_startingup"] = {
    "title": _l("Starting up"),
    "unit": "count",
    "color": "11/a",
}

metric_info["apache_state_waiting"] = {
    "title": _l("Waiting"),
    "unit": "count",
    "color": "14/a",
}

metric_info["apache_state_logging"] = {
    "title": _l("Logging"),
    "unit": "count",
    "color": "21/a",
}

metric_info["apache_state_dns"] = {
    "title": _l("DNS lookup"),
    "unit": "count",
    "color": "24/a",
}

metric_info["apache_state_sending_reply"] = {
    "title": _l("Sending reply"),
    "unit": "count",
    "color": "31/a",
}

metric_info["apache_state_reading_request"] = {
    "title": _l("Reading request"),
    "unit": "count",
    "color": "34/a",
}

metric_info["apache_state_closing"] = {
    "title": _l("Closing connection"),
    "unit": "count",
    "color": "41/a",
}

metric_info["apache_state_idle_cleanup"] = {
    "title": _l("Idle clean up of worker"),
    "unit": "count",
    "color": "44/a",
}

metric_info["apache_state_finishing"] = {
    "title": _l("Gracefully finishing"),
    "unit": "count",
    "color": "46/b",
}

metric_info["apache_state_keep_alive"] = {
    "title": _l("Keepalive"),
    "unit": "count",
    "color": "53/b",
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

graph_info["apache_status"] = {
    "title": _l("Apache status"),
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
