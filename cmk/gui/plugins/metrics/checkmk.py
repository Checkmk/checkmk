#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _l
from cmk.gui.plugins.metrics.utils import graph_info, metric_info, MONITORING_STATUS_COLORS

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

metric_info["host_check_rate"] = {
    "title": _l("Host check rate"),
    "unit": "1/s",
    "color": "52/a",
}

metric_info["monitored_hosts"] = {
    "title": _l("Monitored hosts"),
    "unit": "count",
    "color": "52/b",
}

metric_info["hosts_active"] = {
    "title": _l("Active hosts"),
    "unit": "count",
    "color": "11/a",
}

metric_info["hosts_inactive"] = {
    "title": _l("Inactive hosts"),
    "unit": "count",
    "color": "16/a",
}

metric_info["hosts_degraded"] = {
    "title": _l("Degraded hosts"),
    "unit": "count",
    "color": "23/a",
}

metric_info["hosts_offline"] = {
    "title": _l("Offline hosts"),
    "unit": "count",
    "color": "31/a",
}

metric_info["hosts_other"] = {
    "title": _l("Other hosts"),
    "unit": "count",
    "color": "41/a",
}

metric_info["service_check_rate"] = {
    "title": _l("Service check rate"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["monitored_services"] = {
    "title": _l("Monitored services"),
    "unit": "count",
    "color": "21/b",
}

metric_info["livestatus_connect_rate"] = {
    "title": _l("Livestatus connects"),
    "unit": "1/s",
    "color": "#556677",
}

metric_info["livestatus_request_rate"] = {
    "title": _l("Livestatus requests"),
    "unit": "1/s",
    "color": "#bbccdd",
}

metric_info["helper_usage_cmk"] = {
    "title": _l("Checkmk helper usage"),
    "unit": "%",
    "color": "15/a",
}

metric_info["helper_usage_fetcher"] = {
    "title": _l("Fetcher helper usage"),
    "unit": "%",
    "color": "15/a",
}

metric_info["helper_usage_checker"] = {
    "title": _l("Checker helper usage"),
    "unit": "%",
    "color": "15/a",
}

metric_info["helper_usage_generic"] = {
    "title": _l("Generic helper usage"),
    "unit": "%",
    "color": "41/a",
}

metric_info["average_latency_cmk"] = {
    "title": _l("Checkmk check latency"),
    "unit": "s",
    "color": "15/a",
}

metric_info["average_latency_fetcher"] = {
    "title": _l("Checkmk fetcher latency"),
    "unit": "s",
    "color": "15/a",
}

metric_info["average_latency_generic"] = {
    "title": _l("Check latency"),
    "unit": "s",
    "color": "41/a",
}

metric_info["livestatus_usage"] = {
    "title": _l("Livestatus usage"),
    "unit": "%",
    "color": "12/a",
}

metric_info["livestatus_overflows_rate"] = {
    "title": _l("Livestatus overflows"),
    "unit": "1/s",
    "color": "16/a",
}

metric_info["cmk_time_agent"] = {
    "title": _l("Time spent waiting for Checkmk agent"),
    "unit": "s",
    "color": "36/a",
}

metric_info["cmk_time_snmp"] = {
    "title": _l("Time spent waiting for SNMP responses"),
    "unit": "s",
    "color": "32/a",
}

metric_info["cmk_time_ds"] = {
    "title": _l("Time spent waiting for special agent"),
    "unit": "s",
    "color": "34/a",
}

metric_info["log_message_rate"] = {
    "title": _l("Log messages"),
    "unit": "1/s",
    "color": "#aa44cc",
}

metric_info["normal_updates"] = {
    "title": _l("Pending normal updates"),
    "unit": "count",
    "color": "#c08030",
}

metric_info["security_updates"] = {
    "title": _l("Pending security updates"),
    "unit": "count",
    "color": "#ff0030",
}

# Note: current can be any phase, not only open, but also
# delayed, couting or ack.
metric_info["num_open_events"] = {
    "title": _l("Current events"),
    "unit": "count",
    "color": "26/b",
}

metric_info["num_high_alerts"] = {
    "title": _l("High alerts"),
    "unit": "count",
    "color": "22/a",
}

metric_info["num_disabled_alerts"] = {
    "title": _l("Disabled alerts"),
    "unit": "count",
    "color": "24/a",
}


def register_omd_apache_metrics():
    for ty, unit in [("requests", "1/s"), ("bytes", "bytes/s"), ("secs", "1/s")]:
        metric_info[ty + "_cmk_views"] = {
            "title": "%s: %s" % (_l("Checkmk: Views"), ty.capitalize()),
            "unit": unit,
            "color": "#ff8080",
        }

        metric_info[ty + "_cmk_wato"] = {
            "title": "%s: %s" % (_l("Checkmk: WATO"), ty.capitalize()),
            "unit": unit,
            "color": "#377cab",
        }

        metric_info[ty + "_cmk_bi"] = {
            "title": "%s: %s" % (_l("Checkmk: BI"), ty.capitalize()),
            "unit": unit,
            "color": "#4eb0f2",
        }

        metric_info[ty + "_cmk_snapins"] = {
            "title": "%s: %s" % (_l("Checkmk: Sidebar elements"), ty.capitalize()),
            "unit": unit,
            "color": "#ff4040",
        }

        metric_info[ty + "_cmk_dashboards"] = {
            "title": "%s: %s" % (_l("Checkmk: Dashboards"), ty.capitalize()),
            "unit": unit,
            "color": "#4040ff",
        }

        metric_info[ty + "_cmk_other"] = {
            "title": "%s: %s" % (_l("Checkmk: Other"), ty.capitalize()),
            "unit": unit,
            "color": "#5bb9eb",
        }

        metric_info[ty + "_nagvis_snapin"] = {
            "title": "%s: %s" % (_l("NagVis: Sidebar element"), ty.capitalize()),
            "unit": unit,
            "color": "#f2904e",
        }

        metric_info[ty + "_nagvis_ajax"] = {
            "title": "%s: %s" % (_l("NagVis: AJAX"), ty.capitalize()),
            "unit": unit,
            "color": "#af91eb",
        }

        metric_info[ty + "_nagvis_other"] = {
            "title": "%s: %s" % (_l("NagVis: Other"), ty.capitalize()),
            "unit": unit,
            "color": "#f2df40",
        }

        metric_info[ty + "_images"] = {
            "title": "%s: %s" % (_l("Image"), ty.capitalize()),
            "unit": unit,
            "color": "#91cceb",
        }

        metric_info[ty + "_styles"] = {
            "title": "%s: %s" % (_l("Styles"), ty.capitalize()),
            "unit": unit,
            "color": "#c6f24e",
        }

        metric_info[ty + "_scripts"] = {
            "title": "%s: %s" % (_l("Scripts"), ty.capitalize()),
            "unit": unit,
            "color": "#4ef26c",
        }

        metric_info[ty + "_other"] = {
            "title": "%s: %s" % (_l("Other"), ty.capitalize()),
            "unit": unit,
            "color": "#4eeaf2",
        }


register_omd_apache_metrics()

metric_info["cmk_hosts_up"] = {
    "title": _l("UP hosts"),
    "unit": "count",
    "color": MONITORING_STATUS_COLORS["ok/up"],
}

metric_info["cmk_hosts_down"] = {
    "title": _l("DOWN hosts"),
    "unit": "count",
    "color": MONITORING_STATUS_COLORS["critical/down"],
}

metric_info["cmk_hosts_unreachable"] = {
    "title": _l("Unreachable hosts"),
    "unit": "count",
    "color": MONITORING_STATUS_COLORS["unknown/unreachable"],
}

metric_info["cmk_hosts_in_downtime"] = {
    "title": _l("Hosts in downtime"),
    "unit": "count",
    "color": MONITORING_STATUS_COLORS["in_downtime"],
}

metric_info["cmk_services_ok"] = {
    "title": _l("OK services"),
    "unit": "count",
    "color": MONITORING_STATUS_COLORS["ok/up"],
}

metric_info["cmk_services_in_downtime"] = {
    "title": _l("Services in downtime"),
    "unit": "count",
    "color": MONITORING_STATUS_COLORS["in_downtime"],
}

metric_info["cmk_services_on_down_hosts"] = {
    "title": _l("Services of down hosts"),
    "unit": "count",
    "color": MONITORING_STATUS_COLORS["on_down_host"],
}

metric_info["cmk_services_warning"] = {
    "title": _l("WARNING services"),
    "unit": "count",
    "color": MONITORING_STATUS_COLORS["warning"],
}

metric_info["cmk_services_unknown"] = {
    "title": _l("UNKNOWN services"),
    "unit": "count",
    "color": MONITORING_STATUS_COLORS["unknown/unreachable"],
}

metric_info["cmk_services_critical"] = {
    "title": _l("CRITICAL services"),
    "unit": "count",
    "color": MONITORING_STATUS_COLORS["critical/down"],
}

metric_info["age_oldest"] = {
    "title": _l("Oldest age"),
    "unit": "s",
    "color": "35/a",
}

metric_info["age_youngest"] = {
    "title": _l("Youngest age"),
    "unit": "s",
    "color": "21/a",
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

graph_info["livestatus_requests_per_connection"] = {
    "title": _l("Livestatus Requests per Connection"),
    "metrics": [
        (
            "livestatus_request_rate,livestatus_connect_rate,/#88aa33",
            "area",
            _l("Average requests per connection"),
        ),
    ],
}

graph_info["livestatus_usage"] = {
    "title": _l("Livestatus usage"),
    "metrics": [
        ("livestatus_usage", "area"),
    ],
    "range": (0, 100),
}

graph_info["helper_usage_cmk"] = {
    "title": _l("Checkmk helper usage"),
    "metrics": [
        ("helper_usage_cmk", "area"),
    ],
    "range": (0, 100),
}

graph_info["helper_usage_fetcher"] = {
    "title": _l("Fetcher helper usage"),
    "metrics": [
        ("helper_usage_fetcher", "area"),
    ],
    "range": (0, 100),
}

graph_info["helper_usage_checker"] = {
    "title": _l("Checker helper usage"),
    "metrics": [
        ("helper_usage_checker", "area"),
    ],
    "range": (0, 100),
}

graph_info["helper_usage_generic"] = {
    "title": _l("Generic helper usage"),
    "metrics": [
        ("helper_usage_generic", "area"),
    ],
    "range": (0, 100),
}

graph_info["average_check_latency"] = {
    "title": _l("Average check latency"),
    "metrics": [
        ("average_latency_cmk", "line"),
        ("average_latency_generic", "line"),
    ],
}

graph_info["average_fetcher_latency"] = {
    "title": _l("Average check latency"),
    "metrics": [
        ("average_latency_fetcher", "line"),
        ("average_latency_generic", "line"),
    ],
}

graph_info["pending_updates"] = {
    "title": _l("Pending updates"),
    "metrics": [
        ("normal_updates", "stack"),
        ("security_updates", "stack"),
    ],
}

graph_info["handled_requests"] = {
    "title": _l("Handled Requests"),
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
    "title": _l("Time spent for various page types"),
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
    "title": _l("Bytes sent"),
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
    "title": _l("Host and Service Checks"),
    "metrics": [
        ("host_check_rate", "stack"),
        ("service_check_rate", "stack"),
    ],
}

graph_info["number_of_monitored_hosts_and_services"] = {
    "title": _l("Number of Monitored Hosts and Services"),
    "metrics": [
        ("monitored_hosts", "stack"),
        ("monitored_services", "stack"),
    ],
}

graph_info["livestatus_connects_and_requests"] = {
    "title": _l("Livestatus Connects and Requests"),
    "metrics": [
        ("livestatus_request_rate", "area"),
        ("livestatus_connect_rate", "area"),
    ],
}

graph_info["message_processing"] = {
    "title": _l("Message processing"),
    "metrics": [
        ("average_message_rate", "area"),
        ("average_drop_rate", "area"),
    ],
}

graph_info["rule_efficiency"] = {
    "title": _l("Rule efficiency"),
    "metrics": [
        ("average_rule_trie_rate", "area"),
        ("average_rule_hit_rate", "area"),
    ],
}

graph_info["inbound_and_outbound_messages"] = {
    "title": _l("Inbound and Outbound Messages"),
    "metrics": [
        ("messages_outbound", "stack"),
        ("messages_inbound", "stack"),
    ],
}

graph_info["cmk_hosts_total"] = {
    "title": _l("Total number of hosts"),
    "metrics": [
        (
            "cmk_hosts_up,"
            "cmk_hosts_down,"
            "cmk_hosts_unreachable,"
            "cmk_hosts_in_downtime,"
            "+,+,+#0485d1",
            "stack",
            _l("Total"),
        ),
    ],
}

graph_info["cmk_hosts_not_up"] = {
    "title": _l("Number of problematic hosts"),
    "metrics": [
        (
            "cmk_hosts_down",
            "stack",
        ),
        (
            "cmk_hosts_unreachable",
            "stack",
        ),
        (
            "cmk_hosts_in_downtime",
            "stack",
        ),
    ],
    "omit_zero_metrics": True,
}

graph_info["cmk_services_total"] = {
    "title": _l("Total number of services"),
    "metrics": [
        (
            "cmk_services_ok,"
            "cmk_services_in_downtime,"
            "cmk_services_on_down_hosts,"
            "cmk_services_warning,"
            "cmk_services_unknown,"
            "cmk_services_critical,"
            "+,+,+,+,+#0485d1",
            "stack",
            _l("Total"),
        ),
    ],
}

graph_info["cmk_services_not_ok"] = {
    "title": _l("Number of problematic services"),
    "metrics": [
        (
            "cmk_services_in_downtime",
            "stack",
        ),
        (
            "cmk_services_on_down_hosts",
            "stack",
        ),
        (
            "cmk_services_warning",
            "stack",
        ),
        (
            "cmk_services_unknown",
            "stack",
        ),
        (
            "cmk_services_critical",
            "stack",
        ),
    ],
    "omit_zero_metrics": True,
}
