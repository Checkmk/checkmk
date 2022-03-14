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

graph_info["qos_class_traffic"] = {
    "title": _("QoS class traffic"),
    "metrics": [
        ("qos_outbound_bytes_rate,8,*@bits/s", "area", _("QoS outbound bits")),
        ("qos_dropped_bytes_rate,8,*@bits/s", "-area", _("QoS dropped bits")),
    ],
    "range": ("qos_dropped_bytes_rate:max,8,*,-1,*", "qos_outbound_bytes_rate:max,8,*"),
}
