#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.metrics.utils import metric_info

### prism_protection_domains

metric_info["pd_exclusivesnapshot"] = {
    "title": _("Usage"),
    "unit": "bytes",
    "color": "#00ffc6",
}

metric_info["pd_bandwidth_tx"] = {
    "title": _("Tx"),
    "unit": "count",
    "color": "#888800",
}

metric_info["pd_bandwidth_rx"] = {
    "title": _("Rx"),
    "unit": "count",
    "color": "#880088",
}

### prism_info

metric_info["prism_cluster_mem_used"] = {
    "title": _("Used"),
    "unit": "%",
    "color": "#80FF40",
}

metric_info["prism_cluster_iobw"] = {
    "title": _("IO Bandwith"),
    "unit": "bytes/s",
    "color": "#80FF40",
}

metric_info["prism_cluster_iops"] = {
    "title": _("IOPS"),
    "unit": "count",
    "color": "#80FF40",
}

metric_info["prism_cluster_iolatency"] = {
    "title": _("Latency"),
    "unit": "s",
    "color": "#80FF40",
}
