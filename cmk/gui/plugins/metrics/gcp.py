#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _l
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

metric_info["faas_total_instance_count"] = {
    "title": _l("Total number of instances"),
    "unit": "count",
    "color": "11/a",
}

metric_info["faas_active_instance_count"] = {
    "title": _l("Number of active instances"),
    "unit": "count",
    "color": "12/a",
}

metric_info["faas_execution_count"] = {
    "title": _l("Number of requests"),
    "unit": "count",
    "color": "11/a",
}
metric_info["faas_execution_times"] = {
    "title": _l("Request latency"),
    "unit": "s",
    "color": "12/a",
}
