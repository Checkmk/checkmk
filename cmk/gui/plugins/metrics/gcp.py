#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _l
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

metric_info["faas_total_instance_count"] = {
    "title": _l("Total number of instances"),
    "unit": "count",
    "color": "11/a",
}

metric_info["faas_active_instance_count"] = {
    "title": _l("Number of active instances"),
    "unit": "count",
    "color": "12/a",
}

metric_info["faas_execution_count"] = {
    "title": _l("Number of requests"),
    "unit": "1/s",
    "color": "11/a",
}

metric_info["faas_execution_count_2xx"] = {
    "title": _l("Number of requests with return code class 2xx (success)"),
    "unit": "1/s",
    "color": "12/a",
}

metric_info["faas_execution_count_3xx"] = {
    "title": _l("Number of requests with return code class 3xx (redirection)"),
    "unit": "1/s",
    "color": "13/a",
}


metric_info["faas_execution_count_4xx"] = {
    "title": _l("Number of requests with return code class 4xx (client error)"),
    "unit": "1/s",
    "color": "14/a",
}


metric_info["faas_execution_count_5xx"] = {
    "title": _l("Number of requests with return code class 5xx (server error)"),
    "unit": "1/s",
    "color": "15/a",
}


metric_info["faas_execution_times_50"] = {
    "title": _l("Request latency (50th percentile)"),
    "unit": "s",
    "color": "12/a",
}

metric_info["faas_execution_times_95"] = {
    "title": _l("Request latency (95th percentile)"),
    "unit": "s",
    "color": "14/a",
}

metric_info["faas_execution_times_99"] = {
    "title": _l("Request latency (99th percentile)"),
    "unit": "s",
    "color": "16/a",
}

metric_info["faas_execution_times_2xx_50"] = {
    "title": _l("Request latency with return code class 2xx (success) (50th percentile)"),
    "unit": "s",
    "color": "12/a",
}

metric_info["faas_execution_times_2xx_95"] = {
    "title": _l("Request latency with return code class 2xx (success) (95th percentile)"),
    "unit": "s",
    "color": "14/a",
}

metric_info["faas_execution_times_2xx_99"] = {
    "title": _l("Request latency with return code class 2xx (success) (99th percentile)"),
    "unit": "s",
    "color": "16/a",
}

metric_info["faas_execution_times_3xx_50"] = {
    "title": _l("Request latency with return code class 3xx (redirection) (50th percentile)"),
    "unit": "s",
    "color": "12/a",
}

metric_info["faas_execution_times_3xx_95"] = {
    "title": _l("Request latency with return code class 3xx (redirection) (95th percentile)"),
    "unit": "s",
    "color": "14/a",
}

metric_info["faas_execution_times_3xx_99"] = {
    "title": _l("Request latency with return code class 3xx (redirection) (99th percentile)"),
    "unit": "s",
    "color": "16/a",
}

metric_info["faas_execution_times_4xx_50"] = {
    "title": _l("Request latency with return code class 4xx (client error) (50th percentile)"),
    "unit": "s",
    "color": "12/a",
}

metric_info["faas_execution_times_4xx_95"] = {
    "title": _l("Request latency with return code class 4xx (client error) (95th percentile)"),
    "unit": "s",
    "color": "14/a",
}

metric_info["faas_execution_times_4xx_99"] = {
    "title": _l("Request latency with return code class 4xx (client error) (99th percentile)"),
    "unit": "s",
    "color": "16/a",
}


metric_info["faas_execution_times_5xx_50"] = {
    "title": _l("Request latency with return code class 5xx (server error) (50th percentile)"),
    "unit": "s",
    "color": "12/a",
}

metric_info["faas_execution_times_5xx_95"] = {
    "title": _l("Request latency with return code class 5xx (server error) (95th percentile)"),
    "unit": "s",
    "color": "14/a",
}

metric_info["faas_execution_times_5xx_99"] = {
    "title": _l("Request latency with return code class 5xx (server error) (99th percentile)"),
    "unit": "s",
    "color": "16/a",
}


metric_info["faas_memory_size_absolute_50"] = {
    "title": _l("Memory Size (50th percentile)"),
    "unit": "bytes",
    "color": "12/a",
}

metric_info["faas_memory_size_absolute_95"] = {
    "title": _l("Memory Size (95th percentile)"),
    "unit": "bytes",
    "color": "14/a",
}

metric_info["faas_memory_size_absolute_99"] = {
    "title": _l("Memory Size (99th percentile)"),
    "unit": "bytes",
    "color": "16/a",
}

metric_info["gcp_billable_time"] = {
    "title": _l("Billable time"),
    "unit": "s/s",
    "color": "12/a",
}

graph_info["faas_execution_times"] = {
    "title": _l("Request latencies"),
    "metrics": [
        ("faas_execution_times_50", "line"),
        ("faas_execution_times_95", "line"),
        ("faas_execution_times_99", "line"),
    ],
}

graph_info["faas_execution_times_2xx"] = {
    "title": _l("Request latencies with return code class 2xx (success)"),
    "metrics": [
        ("faas_execution_times_2xx_50", "line"),
        ("faas_execution_times_2xx_95", "line"),
        ("faas_execution_times_2xx_99", "line"),
    ],
}
graph_info["faas_execution_times_3xx"] = {
    "title": _l("Request latencies with return code class 3xx (redirection)"),
    "metrics": [
        ("faas_execution_times_3xx_50", "line"),
        ("faas_execution_times_3xx_95", "line"),
        ("faas_execution_times_3xx_99", "line"),
    ],
}
graph_info["faas_execution_times_4xx"] = {
    "title": _l("Request latencies with return code class 4xx (client error)"),
    "metrics": [
        ("faas_execution_times_4xx_50", "line"),
        ("faas_execution_times_4xx_95", "line"),
        ("faas_execution_times_4xx_99", "line"),
    ],
}
graph_info["faas_execution_times_5xx"] = {
    "title": _l("Request latencies with return code class 5xx (server error)"),
    "metrics": [
        ("faas_execution_times_5xx_50", "line"),
        ("faas_execution_times_5xx_95", "line"),
        ("faas_execution_times_5xx_99", "line"),
    ],
}


graph_info["faas_memory_size_absolute"] = {
    "title": _l("Memory Size"),
    "metrics": [
        ("faas_memory_size_absolute_50", "line"),
        ("faas_memory_size_absolute_95", "line"),
        ("faas_memory_size_absolute_99", "line"),
    ],
}
