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


def register_fireye_metrics():
    for what, color in [
        ("Total", "14/b"),
        ("Infected", "53/b"),
        ("Analyzed", "23/a"),
        ("Bypass", "13/b"),
    ]:
        metric_info_key = "%s_rate" % what.lower()
        metric_info[metric_info_key] = {
            "title": _("%s per Second") % what,
            "unit": "1/s",
            "color": color,
        }

    for what, color in [
        ("Attachment", "14/b"),
        ("URL", "13/b"),
        ("Malicious Attachment", "23/a"),
        ("Malicious URL", "53/b"),
    ]:
        metric_info_key = "fireeye_stat_%s" % what.replace(" ", "").lower()
        metric_info[metric_info_key] = {
            "title": _("Emails containing %s per Second") % what,
            "unit": "1/s",
            "color": color,
        }


register_fireye_metrics()
