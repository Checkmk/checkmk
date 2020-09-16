#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _

from cmk.gui.plugins.metrics import (
    metric_info,
    graph_info,
)

#.
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

metric_info["host_check_rate"] = {
    "title": _("Host check rate"),
    "unit": "1/s",
    "color": "52/a",
}

metric_info["monitored_hosts"] = {
    "title": _("Monitored hosts"),
    "unit": "count",
    "color": "52/b",
}

metric_info["hosts_active"] = {
    "title": _("Active hosts"),
    "unit": "count",
    "color": "11/a",
}

metric_info["hosts_inactive"] = {
    "title": _("Inactive hosts"),
    "unit": "count",
    "color": "16/a",
}

metric_info["hosts_degraded"] = {
    "title": _("Degraded hosts"),
    "unit": "count",
    "color": "23/a",
}

metric_info["hosts_offline"] = {
    "title": _("Offline hosts"),
    "unit": "count",
    "color": "31/a",
}

metric_info["hosts_other"] = {
    "title": _("Other hosts"),
    "unit": "count",
    "color": "41/a",
}

metric_info["service_check_rate"] = {
    "title": _("Service check rate"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["monitored_services"] = {
    "title": _("Monitored services"),
    "unit": "count",
    "color": "21/b",
}

metric_info["livestatus_connect_rate"] = {
    "title": _("Livestatus connects"),
    "unit": "1/s",
    "color": "#556677",
}

metric_info["livestatus_request_rate"] = {
    "title": _("Livestatus requests"),
    "unit": "1/s",
    "color": "#bbccdd",
}

metric_info["helper_usage_cmk"] = {
    "title": _("Checkmk helper usage"),
    "unit": "%",
    "color": "15/a",
}

metric_info["helper_usage_fetcher"] = {
    "title": _("Fetcher helper usage"),
    "unit": "%",
    "color": "15/a",
}

metric_info["helper_usage_checker"] = {
    "title": _("Checker helper usage"),
    "unit": "%",
    "color": "15/a",
}

metric_info["helper_usage_generic"] = {
    "title": _("Generic helper usage"),
    "unit": "%",
    "color": "41/a",
}

metric_info["average_latency_cmk"] = {
    "title": _("Checkmk check latency"),
    "unit": "s",
    "color": "15/a",
}

metric_info["average_latency_generic"] = {
    "title": _("Check latency"),
    "unit": "s",
    "color": "41/a",
}

metric_info["livestatus_usage"] = {
    "title": _("Livestatus usage"),
    "unit": "%",
    "color": "12/a",
}

metric_info["livestatus_overflows_rate"] = {
    "title": _("Livestatus overflows"),
    "unit": "1/s",
    "color": "16/a",
}

metric_info["cmk_time_agent"] = {
    "title": _("Time spent waiting for Checkmk agent"),
    "unit": "s",
    "color": "36/a",
}

metric_info["cmk_time_snmp"] = {
    "title": _("Time spent waiting for SNMP responses"),
    "unit": "s",
    "color": "32/a",
}

metric_info["cmk_time_ds"] = {
    "title": _("Time spent waiting for special agent"),
    "unit": "s",
    "color": "34/a",
}

metric_info["log_message_rate"] = {
    "title": _("Log messages"),
    "unit": "1/s",
    "color": "#aa44cc",
}

metric_info["normal_updates"] = {
    "title": _("Pending normal updates"),
    "unit": "count",
    "color": "#c08030",
}

metric_info["security_updates"] = {
    "title": _("Pending security updates"),
    "unit": "count",
    "color": "#ff0030",
}

# Note: current can be any phase, not only open, but also
# delayed, couting or ack.
metric_info["num_open_events"] = {
    "title": _("Current events"),
    "unit": "count",
    "color": "26/b",
}

metric_info["num_high_alerts"] = {
    "title": _("High alerts"),
    "unit": "count",
    "color": "22/a",
}

metric_info["num_disabled_alerts"] = {
    "title": _("Disabled alerts"),
    "unit": "count",
    "color": "24/a",
}


def register_omd_apache_metrics():
    for ty, unit in [("requests", "1/s"), ("bytes", "bytes/s"), ("secs", "1/s")]:
        metric_info[ty + "_cmk_views"] = {
            "title": _("Checkmk: Views"),
            "unit": unit,
            "color": "#ff8080",
        }

        metric_info[ty + "_cmk_wato"] = {
            "title": _("Checkmk: WATO"),
            "unit": unit,
            "color": "#377cab",
        }

        metric_info[ty + "_cmk_bi"] = {
            "title": _("Checkmk: BI"),
            "unit": unit,
            "color": "#4eb0f2",
        }

        metric_info[ty + "_cmk_snapins"] = {
            "title": _("Checkmk: Snapins"),
            "unit": unit,
            "color": "#ff4040",
        }

        metric_info[ty + "_cmk_dashboards"] = {
            "title": _("Checkmk: Dashboards"),
            "unit": unit,
            "color": "#4040ff",
        }

        metric_info[ty + "_cmk_other"] = {
            "title": _("Checkmk: Other"),
            "unit": unit,
            "color": "#5bb9eb",
        }

        metric_info[ty + "_nagvis_snapin"] = {
            "title": _("NagVis: Snapin"),
            "unit": unit,
            "color": "#f2904e",
        }

        metric_info[ty + "_nagvis_ajax"] = {
            "title": _("NagVis: AJAX"),
            "unit": unit,
            "color": "#af91eb",
        }

        metric_info[ty + "_nagvis_other"] = {
            "title": _("NagVis: Other"),
            "unit": unit,
            "color": "#f2df40",
        }

        metric_info[ty + "_images"] = {
            "title": _("Image"),
            "unit": unit,
            "color": "#91cceb",
        }

        metric_info[ty + "_styles"] = {
            "title": _("Styles"),
            "unit": unit,
            "color": "#c6f24e",
        }

        metric_info[ty + "_scripts"] = {
            "title": _("Scripts"),
            "unit": unit,
            "color": "#4ef26c",
        }

        metric_info[ty + "_other"] = {
            "title": _("Other"),
            "unit": unit,
            "color": "#4eeaf2",
        }


register_omd_apache_metrics()

#.
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

graph_info["livestatus_requests_per_connection"] = {
    "title": _("Livestatus Requests per Connection"),
    "metrics": [("livestatus_request_rate,livestatus_connect_rate,/#88aa33", "area",
                 _("Average requests per connection")),],
}

graph_info["livestatus_usage"] = {
    "metrics": [("livestatus_usage", "area"),],
    "range": (0, 100),
}

graph_info["helper_usage_cmk"] = {
    "metrics": [("helper_usage_cmk", "area"),],
    "range": (0, 100),
}

graph_info["helper_usage_fetcher"] = {
    "metrics": [("helper_usage_fetcher", "area"),],
    "range": (0, 100),
}

graph_info["helper_usage_checker"] = {
    "metrics": [("helper_usage_checker", "area"),],
    "range": (0, 100),
}

graph_info["helper_usage_generic"] = {
    "metrics": [("helper_usage_generic", "area"),],
    "range": (0, 100),
}

graph_info["average_check_latency"] = {
    "title": _("Average check latency"),
    "metrics": [
        ("average_latency_cmk", "line"),
        ("average_latency_generic", "line"),
    ],
}

graph_info["pending_updates"] = {
    "title": _("Pending updates"),
    "metrics": [
        ("normal_updates", "stack"),
        ("security_updates", "stack"),
    ],
}

graph_info["handled_requests"] = {
    "title": _("Handled Requests"),
    "metrics": [
        ("requests_cmk_views", "stack"),
        ("requests_cmk_wato", "stack"),
        ("requests_cmk_bi", "stack"),
        ("requests_cmk_snapins", "stack"),
        ("requests_cmk_dashboards", "stack"),
        ("requests_cmk_other", "stack"),
        ("requests_nagvis_snapin", "stack"),
        ("requests_nagvis_ajax", "stack"),
        ("requests_nagvis_other", "stack"),
        ("requests_images", "stack"),
        ("requests_styles", "stack"),
        ("requests_scripts", "stack"),
        ("requests_other", "stack"),
    ],
    "omit_zero_metrics": True,
}

graph_info["cmk_http_pagetimes"] = {
    "title": _("Time spent for various page types"),
    "metrics": [
        ("secs_cmk_views", "stack"),
        ("secs_cmk_wato", "stack"),
        ("secs_cmk_bi", "stack"),
        ("secs_cmk_snapins", "stack"),
        ("secs_cmk_dashboards", "stack"),
        ("secs_cmk_other", "stack"),
        ("secs_nagvis_snapin", "stack"),
        ("secs_nagvis_ajax", "stack"),
        ("secs_nagvis_other", "stack"),
        ("secs_images", "stack"),
        ("secs_styles", "stack"),
        ("secs_scripts", "stack"),
        ("secs_other", "stack"),
    ],
    "omit_zero_metrics": True,
}

graph_info["cmk_http_traffic"] = {
    "title": _("Bytes sent"),
    "metrics": [
        ("bytes_cmk_views", "stack"),
        ("bytes_cmk_wato", "stack"),
        ("bytes_cmk_bi", "stack"),
        ("bytes_cmk_snapins", "stack"),
        ("bytes_cmk_dashboards", "stack"),
        ("bytes_cmk_other", "stack"),
        ("bytes_nagvis_snapin", "stack"),
        ("bytes_nagvis_ajax", "stack"),
        ("bytes_nagvis_other", "stack"),
        ("bytes_images", "stack"),
        ("bytes_styles", "stack"),
        ("bytes_scripts", "stack"),
        ("bytes_other", "stack"),
    ],
    "omit_zero_metrics": True,
}

graph_info["host_and_service_checks"] = {
    "title": _("Host and Service Checks"),
    "metrics": [
        ("host_check_rate", "stack"),
        ("service_check_rate", "stack"),
    ],
}

graph_info["number_of_monitored_hosts_and_services"] = {
    "title": _("Number of Monitored Hosts and Services"),
    "metrics": [
        ("monitored_hosts", "stack"),
        ("monitored_services", "stack"),
    ],
}

graph_info["livestatus_connects_and_requests"] = {
    "title": _("Livestatus Connects and Requests"),
    "metrics": [
        ("livestatus_request_rate", "area"),
        ("livestatus_connect_rate", "area"),
    ],
}

graph_info["message_processing"] = {
    "title": _("Message processing"),
    "metrics": [
        ("average_message_rate", "area"),
        ("average_drop_rate", "area"),
    ],
}

graph_info["rule_efficiency"] = {
    "title": _("Rule efficiency"),
    "metrics": [
        ("average_rule_trie_rate", "area"),
        ("average_rule_hit_rate", "area"),
    ],
}

graph_info["inbound_and_outbound_messages"] = {
    "title": _("Inbound and Outbound Messages"),
    "metrics": [
        ("messages_outbound", "stack"),
        ("messages_inbound", "stack"),
    ],
}
