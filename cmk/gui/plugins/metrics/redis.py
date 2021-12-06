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

metric_info["clients_connected"] = {
    "title": _("Connected clients"),
    "unit": "count",
    "color": "11/a",
}

metric_info["clients_output"] = {
    "title": _("Longest output list"),
    "unit": "count",
    "color": "14/a",
}

metric_info["clients_input"] = {
    "title": _("Biggest input buffer"),
    "unit": "count",
    "color": "21/a",
}

metric_info["clients_blocked"] = {
    "title": _("Clients pending on a blocking call"),
    "unit": "count",
    "color": "32/a",
}

metric_info["changes_sld"] = {
    "title": _("Changes since last dump"),
    "unit": "count",
    "color": "11/a",
}
