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


def register_varnish_metrics():
    for what, descr, color in [
        ("busy", _("too many"), "11/a"),
        ("unhealthy", _("not attempted"), "13/a"),
        ("req", _("requests"), "15/a"),
        ("recycle", _("recycles"), "21/a"),
        ("retry", _("retry"), "23/a"),
        ("fail", _("failures"), "25/a"),
        ("toolate", _("was closed"), "31/a"),
        ("conn", _("success"), "33/a"),
        ("reuse", _("reuses"), "35/a"),
    ]:
        metric_info_key = "varnish_backend_%s_rate" % what
        metric_info[metric_info_key] = {
            "title": _("Backend Conn. %s") % descr,
            "unit": "1/s",
            "color": color,
        }

    for what, descr, color in [
        ("hit", _("hits"), "11/a"),
        ("miss", _("misses"), "13/a"),
        ("hitpass", _("hits for pass"), "21/a"),
    ]:
        metric_info_key = "varnish_cache_%s_rate" % what
        metric_info[metric_info_key] = {
            "title": _("Cache %s") % descr,
            "unit": "1/s",
            "color": color,
        }

    for what, descr, color in [
        ("drop", _("Connections dropped"), "12/a"),
        ("req", _("Client requests received"), "22/a"),
        ("conn", _("Client connections accepted"), "32/a"),
        ("drop_late", _("Connection dropped late"), "42/a"),
    ]:
        metric_info_key = "varnish_client_%s_rate" % what
        metric_info[metric_info_key] = {
            "title": descr,
            "unit": "1/s",
            "color": color,
        }

    for what, descr, color in [
        ("oldhttp", _("Fetch pre HTTP/1.1 closed"), "11/a"),
        ("head", _("Fetch head"), "13/a"),
        ("eof", _("Fetch EOF"), "15/a"),
        ("zero", _("Fetch zero length"), "21/a"),
        ("304", _("Fetch no body (304)"), "23/a"),
        ("1xx", _("Fetch no body (1xx)"), "25/a"),
        ("204", _("Fetch no body (204)"), "31/a"),
        ("length", _("Fetch with length"), "33/a"),
        ("failed", _("Fetch failed"), "35/a"),
        ("bad", _("Fetch had bad headers"), "41/a"),
        ("close", _("Fetch wanted close"), "43/a"),
        ("chunked", _("Fetch chunked"), "45/a"),
    ]:
        metric_info_key = "varnish_fetch_%s_rate" % what
        metric_info[metric_info_key] = {
            "title": descr,
            "unit": "1/s",
            "color": color,
        }

    for what, descr, color in [
        ("expired", _("Expired objects"), "21/a"),
        ("lru_nuked", _("LRU nuked objects"), "31/a"),
        ("lru_moved", _("LRU moved objects"), "41/a"),
    ]:
        metric_info_key = "varnish_objects_%s_rate" % what
        metric_info[metric_info_key] = {
            "title": descr,
            "unit": "1/s",
            "color": color,
        }

    for what, descr, color in [
        ("", _("Worker threads"), "11/a"),
        ("_lqueue", _("Work request queue length"), "13/a"),
        ("_create", _("Worker threads created"), "15/a"),
        ("_drop", _("Dropped work requests"), "21/a"),
        ("_failed", _("Worker threads not created"), "23/a"),
        ("_queued", _("Queued work requests"), "25/a"),
        ("_max", _("Worker threads limited"), "31/a"),
    ]:
        metric_info_key = "varnish_worker%s_rate" % what
        metric_info[metric_info_key] = {
            "title": descr,
            "unit": "1/s",
            "color": color,
        }


register_varnish_metrics()

# ESI = Edge Side Includes
metric_info["varnish_esi_errors_rate"] = {
    "title": _("ESI Errors"),
    "unit": "1/s",
    "color": "13/a",
}

metric_info["varnish_esi_warnings_rate"] = {
    "title": _("ESI Warnings"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["varnish_backend_success_ratio"] = {
    "title": _("Varnish Backend success ratio"),
    "unit": "%",
    "color": "#60c0c0",
}

metric_info["varnish_worker_thread_ratio"] = {
    "title": _("Varnish Worker thread ratio"),
    "unit": "%",
    "color": "#60c0c0",
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

graph_info["varnish_backend_connections"] = {
    "title": _("Varnish Backend Connections"),
    "metrics": [
        ("varnish_backend_busy_rate", "line"),
        ("varnish_backend_unhealthy_rate", "line"),
        ("varnish_backend_req_rate", "line"),
        ("varnish_backend_recycle_rate", "line"),
        ("varnish_backend_retry_rate", "line"),
        ("varnish_backend_fail_rate", "line"),
        ("varnish_backend_toolate_rate", "line"),
        ("varnish_backend_conn_rate", "line"),
        ("varnish_backend_reuse_rate", "line"),
    ],
}

graph_info["varnish_cache"] = {
    "title": _("Varnish Cache"),
    "metrics": [
        ("varnish_cache_miss_rate", "line"),
        ("varnish_cache_hit_rate", "line"),
        ("varnish_cache_hitpass_rate", "line"),
    ],
}

graph_info["varnish_clients"] = {
    "title": _("Varnish Clients"),
    "metrics": [
        ("varnish_client_req_rate", "line"),
        ("varnish_client_conn_rate", "line"),
        ("varnish_client_drop_rate", "line"),
        ("varnish_client_drop_late_rate", "line"),
    ],
}

graph_info["varnish_esi_errors_and_warnings"] = {
    "title": _("Varnish ESI Errors and Warnings"),
    "metrics": [
        ("varnish_esi_errors_rate", "line"),
        ("varnish_esi_warnings_rate", "line"),
    ],
}

graph_info["varnish_fetch"] = {
    "title": _("Varnish Fetch"),
    "metrics": [
        ("varnish_fetch_oldhttp_rate", "line"),
        ("varnish_fetch_head_rate", "line"),
        ("varnish_fetch_eof_rate", "line"),
        ("varnish_fetch_zero_rate", "line"),
        ("varnish_fetch_304_rate", "line"),
        ("varnish_fetch_length_rate", "line"),
        ("varnish_fetch_failed_rate", "line"),
        ("varnish_fetch_bad_rate", "line"),
        ("varnish_fetch_close_rate", "line"),
        ("varnish_fetch_1xx_rate", "line"),
        ("varnish_fetch_chunked_rate", "line"),
        ("varnish_fetch_204_rate", "line"),
    ],
}

graph_info["varnish_objects"] = {
    "title": _("Varnish Objects"),
    "metrics": [
        ("varnish_objects_expired_rate", "line"),
        ("varnish_objects_lru_nuked_rate", "line"),
        ("varnish_objects_lru_moved_rate", "line"),
    ],
}

graph_info["varnish_worker"] = {
    "title": _("Varnish Worker"),
    "metrics": [
        ("varnish_worker_lqueue_rate", "line"),
        ("varnish_worker_create_rate", "line"),
        ("varnish_worker_drop_rate", "line"),
        ("varnish_worker_rate", "line"),
        ("varnish_worker_failed_rate", "line"),
        ("varnish_worker_queued_rate", "line"),
        ("varnish_worker_max_rate", "line"),
    ],
}
