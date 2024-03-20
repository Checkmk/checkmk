#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing._utils import graph_info, metric_info
from cmk.gui.i18n import _l

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

metric_info["hosts_healthy"] = {
    "title": _l("Healthy hosts"),
    "unit": "count",
    "color": "46/a",
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
    "color": "21/b",
}

metric_info["helper_usage_checker"] = {
    "title": _l("Checker helper usage"),
    "unit": "%",
    "color": "15/a",
}

metric_info["helper_usage_generic"] = {
    "title": _l("Active check helper usage"),
    "unit": "%",
    "color": "41/a",
}

metric_info["average_latency_cmk"] = {
    "title": _l("Checkmk checker latency"),
    "unit": "s",
    "color": "15/a",
}

metric_info["average_latency_fetcher"] = {
    "title": _l("Checkmk fetcher latency"),
    "unit": "s",
    "color": "21/b",
}

metric_info["average_latency_generic"] = {
    "title": _l("Active check latency"),
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

metric_info["perf_data_count_rate"] = {
    "title": _l("Rate of performance data received"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["metrics_count_rate"] = {
    "title": _l("Rate of metrics received"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["influxdb_queue_usage"] = {
    "title": _l("InfluxDB queue usage"),
    "unit": "%",
    "color": "21/a",
}
metric_info["influxdb_queue_usage_rate"] = {
    "title": _l("InfluxDB queue usage rate"),
    "unit": "1/s",
    "color": "21/a",
}
metric_info["influxdb_overflows_rate"] = {
    "title": _l("Rate of performance data loss for InfluxDB"),
    "unit": "1/s",
    "color": "21/a",
}
metric_info["influxdb_bytes_sent_rate"] = {
    "title": _l("Rate of bytes sent to the InfluxDB connection"),
    "unit": "bytes/s",
    "color": "21/a",
}

metric_info["rrdcached_queue_usage"] = {
    "title": _l("RRD queue usage"),
    "unit": "%",
    "color": "21/a",
}
metric_info["rrdcached_queue_usage_rate"] = {
    "title": _l("RRD queue usage rate"),
    "unit": "1/s",
    "color": "21/a",
}
metric_info["rrdcached_overflows_rate"] = {
    "title": _l("Rate of performance data loss for RRD"),
    "unit": "1/s",
    "color": "21/a",
}
metric_info["rrdcached_bytes_sent_rate"] = {
    "title": _l("Rate of bytes sent to the RRD connection"),
    "unit": "bytes/s",
    "color": "21/a",
}

metric_info["carbon_queue_usage"] = {
    "title": _l("Carbon queue usage"),
    "unit": "%",
    "color": "21/a",
}
metric_info["carbon_queue_usage_rate"] = {
    "title": _l("Carbon queue usage rate"),
    "unit": "1/s",
    "color": "21/a",
}
metric_info["carbon_overflows_rate"] = {
    "title": _l("Rate of performance data loss for Carbon"),
    "unit": "1/s",
    "color": "21/a",
}
metric_info["carbon_bytes_sent_rate"] = {
    "title": _l("Rate of bytes sent to the Carbon connection"),
    "unit": "bytes/s",
    "color": "21/a",
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

graph_info["helper_usage"] = {
    "title": _l("Helper usage"),
    "metrics": [
        ("helper_usage_fetcher", "line"),
        ("helper_usage_checker", "line"),
        ("helper_usage_generic", "line"),
    ],
    "range": (0, 100),
}

graph_info["average_helper_latency"] = {
    "title": _l("Average helper latency"),
    "metrics": [
        ("average_latency_fetcher", "line"),
        ("average_latency_cmk", "line"),
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
        ("livestatus_request_rate", "line"),
        ("livestatus_connect_rate", "line"),
    ],
}

graph_info["inbound_and_outbound_messages"] = {
    "title": _l("Inbound and Outbound Messages"),
    "metrics": [
        ("messages_outbound", "stack"),
        ("messages_inbound", "stack"),
    ],
}
