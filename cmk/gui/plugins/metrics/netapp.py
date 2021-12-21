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


def _fix_title(title):
    return title.replace("read data", "data read").replace("write data", "data written")


def register_netapp_api_vs_traffic_metrics():

    metric_info["read_data"] = {
        "title": _("Data read"),
        "unit": "bytes",
        "color": "31/a",
    }

    metric_info["write_data"] = {
        "title": _("Data written"),
        "unit": "bytes",
        "color": "44/a",
    }

    for volume_info in ["NFS", "NFSv4", "NFSv4.1", "CIFS", "SAN", "FCP", "ISCSI"]:
        for what, unit in [
            ("data", "bytes"),
            ("latency", "s"),
            ("ios", "1/s"),
            ("throughput", "bytes/s"),
            ("ops", "1/s"),
        ]:
            volume = volume_info.lower().replace(".", "_")

            metric_info["%s_read_%s" % (volume, what)] = {
                "title": _fix_title(_("%s read %s") % (volume_info, what)),
                "unit": unit,
                "color": "31/a",
            }

            metric_info["%s_write_%s" % (volume, what)] = {
                "title": _fix_title(_("%s write %s") % (volume_info, what)),
                "unit": unit,
                "color": "44/a",
            }

            if what in ["data", "ops", "latency"]:
                metric_info["%s_other_%s" % (volume, what)] = {
                    "title": _("%s other %s") % (volume_info, what),
                    "unit": unit,
                    "color": "21/a",
                }


register_netapp_api_vs_traffic_metrics()

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


def register_netapp_api_vs_traffic_graphs():

    graph_info["read_write_data"] = {
        "title": _("Traffic"),
        "metrics": [
            ("read_data", "-area"),
            ("write_data", "area"),
        ],
    }

    for what, text in [
        ("nfs", "NFS"),
        ("cifs", "CIFS"),
        ("san", "SAN"),
        ("fcp", "FCP"),
        ("iscsi", "iSCSI"),
        ("nfsv4", "NFSv4"),
        ("nfsv4_1", "NFSv4.1"),
    ]:
        graph_info["%s_traffic" % what] = {
            "title": _("%s traffic") % text,
            "metrics": [
                ("%s_read_data" % what, "-area"),
                ("%s_write_data" % what, "area"),
            ],
        }

        graph_info["%s_latency" % what] = {
            "title": _("%s latency") % text,
            "metrics": [
                ("%s_read_latency" % what, "-area"),
                ("%s_write_latency" % what, "area"),
            ],
        }

        graph_info["%s_ops" % what] = {
            "title": _("%s operations") % text,
            "metrics": [
                ("%s_read_ops" % what, "-area"),
                ("%s_write_ops" % what, "area"),
            ],
        }


register_netapp_api_vs_traffic_graphs()
