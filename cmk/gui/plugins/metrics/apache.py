#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
