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

metric_info["mails_received_time"] = {
    "title": _("Received mails"),
    "unit": "s",
    "color": "31/a",
}

metric_info["mail_queue_deferred_length"] = {
    "title": _("Length of deferred mail queue"),
    "unit": "count",
    "color": "#40a0b0",
}

metric_info["mail_queue_active_length"] = {
    "title": _("Length of active mail queue"),
    "unit": "count",
    "color": "#ff6000",
}

metric_info["mail_queue_deferred_size"] = {
    "title": _("Size of deferred mail queue"),
    "unit": "bytes",
    "color": "43/a",
}

metric_info["mail_queue_active_size"] = {
    "title": _("Size of active mail queue"),
    "unit": "bytes",
    "color": "31/a",
}

metric_info["mail_queue_hold_length"] = {
    "title": _("Length of hold mail queue"),
    "unit": "count",
    "color": "26/b",
}

metric_info["mail_queue_incoming_length"] = {
    "title": _("Length of incoming mail queue"),
    "unit": "count",
    "color": "14/b",
}

metric_info["mail_queue_drop_length"] = {
    "title": _("Length of drop mail queue"),
    "unit": "count",
    "color": "51/b",
}

metric_info["mail_received_rate"] = {
    "title": _("Mails received rate"),
    "unit": "1/s",
    "color": "31/a",
}

metric_info["mail_queue_postfix_total"] = {
    "title": _("Total length of Postfix queue"),
    "unit": "count",
    "color": "32/a",
}

metric_info["mail_queue_z1_messenger"] = {
    "title": _("Length of Z1 messenger mail queue"),
    "unit": "count",
    "color": "32/a",
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

graph_info["amount_of_mails_in_queues"] = {
    "title": _("Amount of mails in queues"),
    "metrics": [
        ("mail_queue_deferred_length", "stack"),
        ("mail_queue_active_length", "stack"),
    ],
    "conflicting_metrics": ["mail_queue_postfix_total", "mail_queue_z1_messenger"],
}

graph_info["size_of_mails_in_queues"] = {
    "title": _("Size of mails in queues"),
    "metrics": [
        ("mail_queue_deferred_size", "stack"),
        ("mail_queue_active_size", "stack"),
    ],
    "conflicting_metrics": ["mail_queue_postfix_total", "mail_queue_z1_messenger"],
}

graph_info["amount_of_mails_in_secondary_queues"] = {
    "title": _("Amount of mails in queues"),
    "metrics": [
        ("mail_queue_hold_length", "stack"),
        ("mail_queue_incoming_length", "stack"),
        ("mail_queue_drop_length", "stack"),
    ],
    "conflicting_metrics": ["mail_queue_postfix_total", "mail_queue_z1_messenger"],
}
