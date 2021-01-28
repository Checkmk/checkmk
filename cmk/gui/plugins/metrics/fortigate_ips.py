#!/usr/bin/env python3
# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

from cmk.gui.i18n import _

from cmk.gui.plugins.metrics import (metric_info)

metric_info["fortigate_ips_detected_5min"] = {
    "title": _("Detected within the last 5min"),
    "unit": "count",
    "color": "#60f020",
}

metric_info["fortigate_ips_blocked_5min"] = {
    "title": _("Blocked within the last 5min"),
    "unit": "count",
    "color": "#60f020",
}
