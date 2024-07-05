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

metric_info["temp"] = {
    "title": _("Temperature"),
    "unit": "c",
    "color": "16/a",
}

metric_info["fluidflow"] = {
    "title": _("Fluid flow"),
    "unit": "l/s",
    "color": "#ff6234",
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

metric_info["parts_per_million"] = {
    "color": "42/a",
    "title": _("Parts per Million"),
    "unit": "ppm",
}

metric_info["battery_capacity"] = {
    "title": _("Battery capacity"),
    "unit": "%",
    "color": "13/a",
}

metric_info["battery_seconds_remaining"] = {
    "title": _("Battery time remaining"),
    "unit": "s",
    "color": "21/a",
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

metric_info["fan"] = {
    "title": _("Fan speed"),
    "unit": "rpm",
    "color": "16/b",
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

graph_info["fan_speed"] = {
    "title": _("Fan speed"),
    "metrics": [
        ("fan_speed", "area"),
    ],
}

graph_info["battery_capacity"] = {
    "title": _("Battery capacity"),
    "metrics": [
        ("battery_capacity", "area"),
    ],
    "range": (0, 100),
}

graph_info["optical_signal_power"] = {
    "title": _("Optical Signal Power"),
    "metrics": [("rx_light", "line"), ("tx_light", "line")],
}

for i in range(10):
    graph_info["optical_signal_power_lane_%d" % i] = {
        "title": _("Optical Signal Power Lane %d") % i,
        "metrics": [("rx_light_%d" % i, "line"), ("tx_light_%d" % i, "line")],
    }

graph_info["temperature"] = {
    "title": _("Temperature"),
    "metrics": [
        ("temp", "area"),
    ],
    "scalars": [
        "temp:warn",
        "temp:crit",
    ],
}
