#!/usr/bin/env python3
# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

from cmk.gui.i18n import _

from cmk.gui.plugins.metrics import (
    metric_info,
    perfometer_info,
)

metric_info["fortisandbox_disk_usage"] = {
    "title": _("Disk usage"),
    "unit": "%",
    "color": "#60f020",
}
perfometer_info.append({
    "metric": "fortisandbox_disk_usage",
    "type": "linear",
    "segments": ["fortisandbox_disk_usage"],
    "total": 100.0,
})
