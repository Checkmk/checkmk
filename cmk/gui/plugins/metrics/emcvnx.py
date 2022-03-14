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

# EMC VNX storage pools metrics
metric_info["emcvnx_consumed_capacity"] = {
    "title": _("Consumed capacity"),
    "unit": "bytes",
    "color": "13/a",
}

metric_info["emcvnx_avail_capacity"] = {
    "title": _("Available capacity"),
    "unit": "bytes",
    "color": "21/a",
}

metric_info["emcvnx_over_subscribed"] = {
    "title": _("Oversubscribed"),
    "unit": "bytes",
    "color": "13/a",
}

metric_info["emcvnx_total_subscribed_capacity"] = {
    "title": _("Total subscribed capacity"),
    "unit": "bytes",
    "color": "31/a",
}

metric_info["emcvnx_perc_full"] = {
    "title": _("Percent full"),
    "unit": "%",
    "color": "11/a",
}

metric_info["emcvnx_perc_subscribed"] = {
    "title": _("Percent subscribed"),
    "unit": "%",
    "color": "21/a",
}

metric_info["emcvnx_move_up"] = {
    "title": _("Data to move up"),
    "unit": "bytes",
    "color": "11/a",
}

metric_info["emcvnx_move_down"] = {
    "title": _("Data to move down"),
    "unit": "bytes",
    "color": "21/a",
}

metric_info["emcvnx_move_within"] = {
    "title": _("Data to move within"),
    "unit": "bytes",
    "color": "31/a",
}

metric_info["emcvnx_move_completed"] = {
    "title": _("Data movement completed"),
    "unit": "bytes",
    "color": "41/a",
}

metric_info["emcvnx_targeted_higher"] = {
    "title": _("Data targeted for higher tier"),
    "unit": "bytes",
    "color": "11/a",
}

metric_info["emcvnx_targeted_lower"] = {
    "title": _("Data targeted for lower tier"),
    "unit": "bytes",
    "color": "21/a",
}

metric_info["emcvnx_targeted_within"] = {
    "title": _("Data targeted for within tier"),
    "unit": "bytes",
    "color": "31/a",
}

metric_info["emcvnx_time_to_complete"] = {
    "title": _("Estimated time to complete"),
    "unit": "s",
    "color": "31/a",
}

metric_info["emcvnx_dedupl_perc_completed"] = {
    "title": _("Deduplication percent completed"),
    "unit": "%",
    "color": "11/a",
}

metric_info["emcvnx_dedupl_efficiency_savings"] = {
    "title": _("Deduplication efficiency savings"),
    "unit": "bytes",
    "color": "11/a",
}

metric_info["emcvnx_dedupl_remaining_size"] = {
    "title": _("Deduplication remaining size"),
    "unit": "bytes",
    "color": "21/a",
}

metric_info["emcvnx_dedupl_shared_capacity"] = {
    "title": _("Deduplication shared capacity"),
    "unit": "bytes",
    "color": "31/a",
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

graph_info["emcvnx_storage_pools_capacity"] = {
    "title": _("EMC VNX storage pools capacity"),
    "metrics": [
        ("emcvnx_consumed_capacity", "area"),
        ("emcvnx_avail_capacity", "stack"),
    ],
}

graph_info["emcvnx_storage_pools_movement"] = {
    "title": _("EMC VNX storage pools movement"),
    "metrics": [
        ("emcvnx_move_up", "area"),
        ("emcvnx_move_down", "stack"),
        ("emcvnx_move_within", "stack"),
    ],
}

graph_info["emcvnx_storage_pools_targeted"] = {
    "title": _("EMC VNX storage pools targeted tiers"),
    "metrics": [
        ("emcvnx_targeted_higher", "area"),
        ("emcvnx_targeted_lower", "stack"),
        ("emcvnx_targeted_within", "stack"),
    ],
}
