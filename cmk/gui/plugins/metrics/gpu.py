#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
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


metric_info["gpu_utilization"] = {
    "title": _("GPU utilization"),
    "color": "34/a",
    "unit": "%",
}

metric_info["decoder_utilization"] = {
    "title": _("Decoder utilization"),
    "color": "12/a",
    "unit": "%",
}

metric_info["encoder_utilization"] = {
    "title": _("Encoder utilization"),
    "color": "13/a",
    "unit": "%",
}

metric_info["bar1_mem_usage_free"] = {
    "title": _("BAR1 memory usage (free)"),
    "color": "11/a",
    "unit": "bytes",
}

metric_info["bar1_mem_usage_used"] = {
    "title": _("BAR1 memory usage (used)"),
    "color": "14/a",
    "unit": "bytes",
}

metric_info["bar1_mem_usage_total"] = {
    "title": _("BAR1 memory usage (total)"),
    "color": "22/a",
    "unit": "bytes",
}

graph_info["bar1_mem_usage"] = {
    "title": _("BAR1 memory usage"),
    "metrics": [
        ("bar1_mem_usage_used", "stack"),
        ("bar1_mem_usage_free", "stack"),
        ("bar1_mem_usage_total", "line"),
    ],
}
metric_info["fb_mem_usage_free"] = {
    "title": _("FB memory usage (free)"),
    "color": "11/a",
    "unit": "bytes",
}

metric_info["fb_mem_usage_used"] = {
    "title": _("FB memory usage (used)"),
    "color": "14/a",
    "unit": "bytes",
}

metric_info["fb_mem_usage_total"] = {
    "title": _("FB memory usage (total)"),
    "color": "26/a",
    "unit": "bytes",
}

graph_info["fb_mem_usage"] = {
    "title": _("FB memory usage"),
    "metrics": [
        ("fb_mem_usage_used", "stack"),
        ("fb_mem_usage_free", "stack"),
        ("fb_mem_usage_total", "line"),
    ],
}
