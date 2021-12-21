#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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

metric_info["temp"] = {
    "title": _("Temperature"),
    "unit": "c",
    "color": "16/a",
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
    # xgettext: no-python-format
    "title": _("Electrical tension in % of normal value"),
    "unit": "%",
    "color": "#ffc020",
}

metric_info["humidity"] = {
    "title": _("Relative humidity"),
    "unit": "%",
    "color": "#90b0b0",
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

metric_info["frequency"] = {
    "title": _("Frequency"),
    "unit": "hz",
    "color": "11/c",
}

metric_info["battery_capacity"] = {
    "title": _("Battery capacity"),
    "unit": "%",
    "color": "13/a",
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

metric_info["battery_seconds_remaining"] = {
    "title": _("Battery time remaining"),
    "unit": "s",
    "color": "21/a",
}

metric_info["o2_percentage"] = {
    "title": _("Current O2 percentage"),
    "unit": "%",
    "color": "42/a",
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

graph_info["battery_currents"] = {
    "title": _("Battery currents"),
    "metrics": [
        ("battery_current", "area"),
        ("current", "stack"),
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
