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

metric_info["printer_queue"] = {
    "title": _("Printer queue length"),
    "unit": "count",
    "color": "#a63df2",
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

# Printer

graph_info["printer_queue"] = {
    "title": _("Printer queue length"),
    "metrics": [("printer_queue", "area")],
    "range": (0, 10),
}

graph_info["supply_toner_cyan"] = {
    "title": _("Supply toner cyan"),
    "metrics": [("supply_toner_cyan", "area")],
    "range": (0, 100),
}

graph_info["supply_toner_magenta"] = {
    "title": _("Supply toner magenta"),
    "metrics": [("supply_toner_magenta", "area")],
    "range": (0, 100),
}

graph_info["supply_toner_yellow"] = {
    "title": _("Supply toner yellow"),
    "metrics": [("supply_toner_yellow", "area")],
    "range": (0, 100),
}

graph_info["supply_toner_black"] = {
    "title": _("Supply toner black"),
    "metrics": [("supply_toner_black", "area")],
    "range": (0, 100),
}

graph_info["supply_toner_other"] = {
    "title": _("Supply toner"),
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
