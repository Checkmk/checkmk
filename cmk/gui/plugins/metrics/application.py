#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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

metric_info["major_page_faults"] = {
    "title": _l("Major page faults"),
    "unit": "1/s",
    "color": "#20ff80",
}

metric_info["page_swap_in"] = {
    "title": _l("Page Swap In"),
    "unit": "1/s",
    "color": "33/a",
}

metric_info["page_swap_out"] = {
    "title": _l("Page Swap Out"),
    "unit": "1/s",
    "color": "36/a",
}

metric_info["uncommitted"] = {
    "title": _l("Uncommitted"),
    "unit": "bytes",
    "color": "16/a",
}

metric_info["overprovisioned"] = {
    "title": _l("Overprovisioned"),
    "unit": "bytes",
    "color": "24/a",
}

metric_info["precompiled"] = {
    "title": _l("Precompiled"),
    "unit": "bytes",
    "color": "16/a",
}

metric_info["codewords_corrected"] = {
    "title": _l("Corrected codewords"),
    "unit": "%",
    "color": "#ff8040",
}

metric_info["codewords_uncorrectable"] = {
    "title": _l("Uncorrectable codewords"),
    "unit": "%",
    "color": "#ff4020",
}

metric_info["xda_hitratio"] = {
    "title": _l("XDA hitratio"),
    "unit": "%",
    "color": "#0ae86d",
}

metric_info["data_hitratio"] = {
    "title": _l("Data hitratio"),
    "unit": "%",
    "color": "#2828de",
}

metric_info["index_hitratio"] = {
    "title": _l("Index hitratio"),
    "unit": "%",
    "color": "#dc359f",
}

metric_info["total_hitratio"] = {
    "title": _l("Total hitratio"),
    "unit": "%",
    "color": "#2e282c",
}

metric_info["deadlocks"] = {
    "title": _l("Deadlocks"),
    "unit": "1/s",
    "color": "#dc359f",
}

metric_info["lockwaits"] = {
    "title": _l("Waitlocks"),
    "unit": "1/s",
    "color": "#2e282c",
}

metric_info["sort_overflow"] = {
    "title": _l("Sort overflow"),
    "unit": "%",
    "color": "#e72121",
}

metric_info["hours_operation"] = {
    "title": _l("Hours of operation"),
    "unit": "s",
    "color": "#94b65a",
}

metric_info["hours_since_service"] = {
    "title": _l("Hours since service"),
    "unit": "s",
    "color": "#94b65a",
}

metric_info["execution_time"] = {
    "title": _l("Total execution time"),
    "unit": "s",
    "color": "#d080af",
}

metric_info["user_time"] = {
    "title": _l("CPU time in user space"),
    "unit": "s",
    "color": "#60f020",
}

metric_info["registered_phones"] = {
    "title": _l("Registered phones"),
    "unit": "count",
    "color": "#60bbbb",
}

metric_info["messages"] = {
    "title": _l("Messages"),
    "unit": "count",
    "color": "#aa44cc",
}

metric_info["call_legs"] = {
    "title": _l("Call legs"),
    "unit": "count",
    "color": "#60bbbb",
}

metric_info["messages_inbound"] = {
    "title": _l("Inbound messages"),
    "unit": "1/s",
    "color": "31/a",
}

metric_info["messages_outbound"] = {
    "title": _l("Outbound messages"),
    "unit": "1/s",
    "color": "36/a",
}

metric_info["licenses"] = {
    "title": _l("Used licenses"),
    "unit": "count",
    "color": "#ff6234",
}

metric_info["license_percentage"] = {
    "title": _l("Used licenses"),
    "unit": "%",
    "color": "16/a",
}

metric_info["licenses_total"] = {
    "title": _l("Total licenses"),
    "unit": "count",
    "color": "16/b",
}

metric_info["license_size"] = {
    "title": _l("Size of license"),
    "unit": "bytes",
    "color": "11/a",
}

metric_info["license_usage"] = {
    "title": _l("License usage"),
    "unit": "%",
    "color": "13/a",
}

metric_info["database_apply_lag"] = {
    "title": _l("Database apply lag"),
    "help": _l(
        "Amount of time that the application of redo data on the standby database lags behind the primary database"
    ),
    "unit": "s",
    "color": "#006040",
}

metric_info["jvm_garbage_collection_count"] = {
    "title": _l("Garbage collections"),
    "unit": "1/s",
    "color": "31/a",
}

metric_info["jvm_garbage_collection_time"] = {
    "title": _l("Time spent collecting garbage"),
    "unit": "%",
    "color": "32/a",
}

metric_info["registered_desktops"] = {
    "title": _l("Registered desktops"),
    "unit": "count",
    "color": "16/d",
}

metric_info["time_in_GC"] = {
    "title": _l("Time spent in GC"),
    "unit": "%",
    "color": "16/a",
}

metric_info["db_read_latency"] = {
    "title": _l("Read latency"),
    "unit": "s",
    "color": "35/a",
}

metric_info["db_read_recovery_latency"] = {
    "title": _l("Read recovery latency"),
    "unit": "s",
    "color": "31/a",
}

metric_info["db_write_latency"] = {
    "title": _l("Write latency"),
    "unit": "s",
    "color": "45/a",
}

metric_info["db_log_latency"] = {
    "title": _l("Log latency"),
    "unit": "s",
    "color": "25/a",
}

metric_info["active_vms"] = {
    "title": _l("Active VMs"),
    "unit": "count",
    "color": "14/a",
}

metric_info["quarantine"] = {
    "title": _l("Quarantine Usage"),
    "unit": "%",
    "color": "43/b",
}

metric_info["messages_in_queue"] = {
    "title": _l("Messages in queue"),
    "unit": "count",
    "color": "16/a",
}

metric_info["service_costs_eur"] = {
    "title": _l("Service Costs per Day"),
    "unit": "EUR",
    "color": "35/a",
}

metric_info["elapsed_time"] = {
    "title": _l("Elapsed time"),
    "unit": "s",
    "color": "11/a",
}

metric_info["splunk_slave_usage_bytes"] = {
    "title": _l("Slave usage bytes across all pools"),
    "unit": "bytes",
    "color": "11/a",
}

metric_info["fired_alerts"] = {
    "title": _l("Number of fired alerts"),
    "unit": "count",
    "color": "22/a",
}

metric_info["msgs_avg"] = {
    "title": _l("Average number of messages"),
    "unit": "count",
    "color": "23/a",
}

metric_info["index_count"] = {
    "title": _l("Indices"),
    "unit": "count",
    "color": "23/a",
}

metric_info["items_active"] = {
    "title": _l("Active items"),
    "unit": "count",
    "color": "23/a",
}

metric_info["items_non_res"] = {
    "title": _l("Non-resident items"),
    "unit": "count",
    "color": "23/a",
}

metric_info["items_count"] = {
    "title": _l("Items"),
    "unit": "count",
    "color": "23/a",
}

metric_info["num_collections"] = {
    "title": _l("Collections"),
    "unit": "count",
    "color": "11/a",
}

metric_info["num_objects"] = {
    "title": _l("Objects"),
    "unit": "count",
    "color": "14/a",
}

metric_info["num_extents"] = {
    "title": _l("Extents"),
    "unit": "count",
    "color": "16/a",
}

metric_info["num_input"] = {
    "title": _l("Inputs"),
    "unit": "count",
    "color": "11/a",
}

metric_info["num_output"] = {
    "title": _l("Outputs"),
    "unit": "count",
    "color": "14/a",
}

metric_info["num_stream_rule"] = {
    "title": _l("Stream rules"),
    "unit": "count",
    "color": "16/a",
}

metric_info["num_extractor"] = {
    "title": _l("Extractors"),
    "unit": "count",
    "color": "21/a",
}

metric_info["num_user"] = {
    "title": _l("User"),
    "unit": "count",
    "color": "23/a",
}

# DRBD metrics
metric_info["activity_log_updates"] = {
    "title": _l("Activity log updates"),
    "unit": "count",
    "color": "31/a",
}

metric_info["bit_map_updates"] = {
    "title": _l("Bit map updates"),
    "unit": "count",
    "color": "32/a",
}

metric_info["local_count_requests"] = {
    "title": _l("Local count requests"),
    "unit": "count",
    "color": "24/b",
}

metric_info["pending_requests"] = {
    "title": _l("Pending requests"),
    "unit": "count",
    "color": "16/a",
}

metric_info["unacknowledged_requests"] = {
    "title": _l("Unacknowledged requests"),
    "unit": "count",
    "color": "16/b",
}

metric_info["application_pending_requests"] = {
    "title": _l("Application pending requests"),
    "unit": "count",
    "color": "23/a",
}

metric_info["epoch_objects"] = {
    "title": _l("Epoch objects"),
    "unit": "count",
    "color": "42/a",
}

metric_info["graylog_input"] = {
    "title": _l("Input traffic"),
    "unit": "bytes",
    "color": "16/b",
}

metric_info["graylog_output"] = {
    "title": _l("Output traffic"),
    "unit": "bytes",
    "color": "23/a",
}

metric_info["graylog_decoded"] = {
    "title": _l("Decoded traffic"),
    "unit": "bytes",
    "color": "42/a",
}

metric_info["graylog_diff"] = {
    "title": _l("Number of messages in defined timespan"),
    "unit": "count",
    "color": "11/a",
}

metric_info["collectors_running"] = {
    "title": _l("Running collectors"),
    "unit": "count",
    "color": "26/a",
}
metric_info["collectors_stopped"] = {
    "title": _l("Stopped collectors"),
    "unit": "count",
    "color": "21/a",
}
metric_info["collectors_failing"] = {
    "title": _l("Failing collectors"),
    "unit": "count",
    "color": "12/a",
}

metric_info["num_streams"] = {
    "title": _l("Streams"),
    "unit": "count",
    "color": "11/a",
}

metric_info["item_memory"] = {
    "color": "26/a",
    "title": _l("Item memory"),
    "unit": "bytes",
}

metric_info["resident_items_ratio"] = {
    "title": _l("Resident items ratio"),
    "unit": "%",
    "color": "23/a",
}

metric_info["fetched_items"] = {
    "title": _l("Number of fetched items"),
    "unit": "count",
    "color": "23/b",
}

metric_info["jira_count"] = {
    "title": _l("Number of issues"),
    "unit": "count",
    "color": "14/a",
}

metric_info["jira_sum"] = {
    "title": _l("Result of summed up values"),
    "unit": "count",
    "color": "14/a",
}

metric_info["jira_avg"] = {
    "title": _l("Average value"),
    "unit": "count",
    "color": "14/a",
}

metric_info["jira_diff"] = {
    "title": _l("Difference"),
    "unit": "count",
    "color": "11/a",
}

metric_info["consumers"] = {
    "title": _l("Consumers"),
    "unit": "count",
    "color": "21/a",
}

metric_info["exchanges"] = {
    "title": _l("Exchanges"),
    "unit": "count",
    "color": "26/a",
}

metric_info["queues"] = {
    "title": _l("Queues"),
    "unit": "count",
    "color": "31/a",
}

metric_info["messages_rate"] = {
    "title": _l("Message Rate"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["messages_ready"] = {
    "title": _l("Ready messages"),
    "unit": "count",
    "color": "11/a",
}

metric_info["messages_unacknowledged"] = {
    "title": _l("Unacknowledged messages"),
    "unit": "count",
    "color": "14/a",
}

metric_info["messages_publish"] = {
    "title": _l("Published messages"),
    "unit": "count",
    "color": "31/a",
}

metric_info["messages_publish_rate"] = {
    "title": _l("Published message rate"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["messages_deliver"] = {
    "title": _l("Delivered messages"),
    "unit": "count",
    "color": "26/a",
}

metric_info["messages_deliver_rate"] = {
    "title": _l("Delivered message rate"),
    "unit": "1/s",
    "color": "53/a",
}

metric_info["gc_runs"] = {
    "title": _l("GC runs"),
    "unit": "count",
    "color": "31/a",
}

metric_info["gc_runs_rate"] = {
    "title": _l("GC runs rate"),
    "unit": "1/s",
    "color": "53/a",
}

metric_info["runtime_run_queue"] = {
    "title": _l("Runtime run queue"),
    "unit": "count",
    "color": "21/a",
}

metric_info["gc_bytes"] = {
    "title": _l("Bytes reclaimed by GC"),
    "unit": "bytes",
    "color": "32/a",
}

metric_info["gc_bytes_rate"] = {
    "title": _l("Bytes reclaimed by GC rate"),
    "unit": "bytes/s",
    "color": "42/a",
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

# TODO: Warum ist hier überall line? Default ist Area.
# Kann man die hit ratios nicht schön stacken? Ist
# nicht total die Summe der anderen?

graph_info["bufferpool_hitratios"] = {
    "title": _l("Bufferpool Hitratios"),
    "metrics": [
        ("total_hitratio", "line"),
        ("data_hitratio", "line"),
        ("index_hitratio", "line"),
        ("xda_hitratio", "line"),
    ],
}

graph_info["deadlocks_and_waits"] = {
    "title": _l("Dead- and waitlocks"),
    "metrics": [
        ("deadlocks", "area"),
        ("lockwaits", "stack"),
    ],
}

graph_info["licenses"] = {
    "title": _l("Licenses"),
    "metrics": [
        (
            "licenses_total",
            "area",
        ),
        (
            "licenses",
            "area",
        ),
    ],
}

graph_info["current_users"] = {
    "title": _l("Number of signed-in users"),
    "metrics": [
        ("current_users", "area"),
    ],
    "scalars": [
        "current_users:warn",
        "current_users:crit",
    ],
}
