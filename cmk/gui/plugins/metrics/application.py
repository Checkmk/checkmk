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

metric_info["major_page_faults"] = {
    "title": _("Major page faults"),
    "unit": "1/s",
    "color": "#20ff80",
}

metric_info["page_swap_in"] = {
    "title": _("Page Swap In"),
    "unit": "1/s",
    "color": "33/a",
}

metric_info["page_swap_out"] = {
    "title": _("Page Swap Out"),
    "unit": "1/s",
    "color": "36/a",
}

metric_info["uncommitted"] = {
    "title": _("Uncommitted"),
    "unit": "bytes",
    "color": "16/a",
}

metric_info["overprovisioned"] = {
    "title": _("Overprovisioned"),
    "unit": "bytes",
    "color": "24/a",
}

metric_info["precompiled"] = {
    "title": _("Precompiled"),
    "unit": "bytes",
    "color": "16/a",
}

metric_info["codewords_corrected"] = {
    "title": _("Corrected codewords"),
    "unit": "%",
    "color": "#ff8040",
}

metric_info["codewords_uncorrectable"] = {
    "title": _("Uncorrectable codewords"),
    "unit": "%",
    "color": "#ff4020",
}

metric_info["xda_hitratio"] = {
    "title": _("XDA hitratio"),
    "unit": "%",
    "color": "#0ae86d",
}

metric_info["data_hitratio"] = {
    "title": _("Data hitratio"),
    "unit": "%",
    "color": "#2828de",
}

metric_info["index_hitratio"] = {
    "title": _("Index hitratio"),
    "unit": "%",
    "color": "#dc359f",
}

metric_info["total_hitratio"] = {
    "title": _("Total hitratio"),
    "unit": "%",
    "color": "#2e282c",
}

metric_info["deadlocks"] = {
    "title": _("Deadlocks"),
    "unit": "1/s",
    "color": "#dc359f",
}

metric_info["lockwaits"] = {
    "title": _("Waitlocks"),
    "unit": "1/s",
    "color": "#2e282c",
}

metric_info["sort_overflow"] = {
    "title": _("Sort overflow"),
    "unit": "%",
    "color": "#e72121",
}

metric_info["hours_operation"] = {
    "title": _("Hours of operation"),
    "unit": "s",
    "color": "#94b65a",
}

metric_info["hours_since_service"] = {
    "title": _("Hours since service"),
    "unit": "s",
    "color": "#94b65a",
}

metric_info["execution_time"] = {
    "title": _("Total execution time"),
    "unit": "s",
    "color": "#d080af",
}

metric_info["user_time"] = {
    "title": _("CPU time in user space"),
    "unit": "s",
    "color": "#60f020",
}

metric_info["registered_phones"] = {
    "title": _("Registered phones"),
    "unit": "count",
    "color": "#60bbbb",
}

metric_info["messages"] = {
    "title": _("Messages"),
    "unit": "count",
    "color": "#aa44cc",
}

metric_info["call_legs"] = {
    "title": _("Call legs"),
    "unit": "count",
    "color": "#60bbbb",
}

metric_info["messages_inbound"] = {
    "title": _("Inbound messages"),
    "unit": "1/s",
    "color": "31/a",
}

metric_info["messages_outbound"] = {
    "title": _("Outbound messages"),
    "unit": "1/s",
    "color": "36/a",
}

metric_info["licenses"] = {
    "title": _("Used licenses"),
    "unit": "count",
    "color": "#ff6234",
}

metric_info["license_percentage"] = {
    "title": _("Used licenses"),
    "unit": "%",
    "color": "16/a",
}

metric_info["licenses_total"] = {
    "title": _("Total licenses"),
    "unit": "count",
    "color": "16/b",
}

metric_info["license_size"] = {
    "title": _("Size of license"),
    "unit": "bytes",
    "color": "11/a",
}

metric_info["license_usage"] = {
    "title": _("License usage"),
    "unit": "%",
    "color": "13/a",
}

metric_info["database_apply_lag"] = {
    "title": _("Database apply lag"),
    "help": _(
        "Amount of time that the application of redo data on the standby database lags behind the primary database"
    ),
    "unit": "s",
    "color": "#006040",
}

metric_info["jvm_garbage_collection_count"] = {
    "title": _("Garbage collections"),
    "unit": "1/s",
    "color": "31/a",
}

metric_info["jvm_garbage_collection_time"] = {
    "title": _("Time spent collecting garbage"),
    "unit": "%",
    "color": "32/a",
}

metric_info["registered_desktops"] = {
    "title": _("Registered desktops"),
    "unit": "count",
    "color": "16/d",
}

metric_info["time_in_GC"] = {
    "title": _("Time spent in GC"),
    "unit": "%",
    "color": "16/a",
}

metric_info["db_read_latency"] = {
    "title": _("Read latency"),
    "unit": "s",
    "color": "35/a",
}

metric_info["db_read_recovery_latency"] = {
    "title": _("Read recovery latency"),
    "unit": "s",
    "color": "31/a",
}

metric_info["db_write_latency"] = {
    "title": _("Write latency"),
    "unit": "s",
    "color": "45/a",
}

metric_info["db_log_latency"] = {
    "title": _("Log latency"),
    "unit": "s",
    "color": "25/a",
}

metric_info["ready_replicas"] = {
    "title": _("Ready replicas"),
    "unit": "",
    "color": "21/a",
}

metric_info["total_replicas"] = {
    "title": _("Total replicas"),
    "unit": "",
    "color": "35/a",
}

metric_info["active_vms"] = {
    "title": _("Active VMs"),
    "unit": "count",
    "color": "14/a",
}

metric_info["quarantine"] = {
    "title": _("Quarantine Usage"),
    "unit": "%",
    "color": "43/b",
}

metric_info["messages_in_queue"] = {
    "title": _("Messages in queue"),
    "unit": "count",
    "color": "16/a",
}

metric_info['service_costs_eur'] = {
    'title': _('Service Costs per Day'),
    'unit': 'EUR',
    'color': '35/a',
}

metric_info["elapsed_time"] = {
    "title": _("Elapsed time"),
    "unit": "s",
    "color": "11/a",
}

metric_info["splunk_slave_usage_bytes"] = {
    "title": _("Slave usage bytes across all pools"),
    "unit": "bytes",
    "color": "11/a",
}

metric_info["fired_alerts"] = {
    "title": _("Number of fired alerts"),
    "unit": "count",
    "color": "22/a",
}

metric_info["msgs_avg"] = {
    "title": _("Average number of messages"),
    "unit": "count",
    "color": "23/a",
}

metric_info["index_count"] = {
    "title": _("Indices"),
    "unit": "count",
    "color": "23/a",
}

metric_info["items_active"] = {
    "title": _("Active items"),
    "unit": "count",
    "color": "23/a",
}

metric_info["items_non_res"] = {
    "title": _("Non-resident items"),
    "unit": "count",
    "color": "23/a",
}

metric_info["items_count"] = {
    "title": _("Items"),
    "unit": "count",
    "color": "23/a",
}

metric_info["num_collections"] = {
    "title": _("Collections"),
    "unit": "count",
    "color": "11/a",
}

metric_info["num_objects"] = {
    "title": _("Objects"),
    "unit": "count",
    "color": "14/a",
}

metric_info["num_extents"] = {
    "title": _("Extents"),
    "unit": "count",
    "color": "16/a",
}

metric_info["num_input"] = {
    "title": _("Inputs"),
    "unit": "count",
    "color": "11/a",
}

metric_info["num_output"] = {
    "title": _("Outputs"),
    "unit": "count",
    "color": "14/a",
}

metric_info["num_stream_rule"] = {
    "title": _("Stream rules"),
    "unit": "count",
    "color": "16/a",
}

metric_info["num_extractor"] = {
    "title": _("Extractors"),
    "unit": "count",
    "color": "21/a",
}

metric_info["num_user"] = {
    "title": _("User"),
    "unit": "count",
    "color": "23/a",
}

# DRBD metrics
metric_info['activity_log_updates'] = {
    "title": _("Activity log updates"),
    "unit": "count",
    "color": "31/a",
}

metric_info['bit_map_updates'] = {
    "title": _("Bit map updates"),
    "unit": "count",
    "color": "32/a",
}

metric_info['local_count_requests'] = {
    "title": _("Local count requests"),
    "unit": "count",
    "color": "24/b",
}

metric_info['pending_requests'] = {
    "title": _("Pending requests"),
    "unit": "count",
    "color": "16/a",
}

metric_info['unacknowledged_requests'] = {
    "title": _("Unacknowledged requests"),
    "unit": "count",
    "color": "16/b",
}

metric_info['application_pending_requests'] = {
    "title": _("Application pending requests"),
    "unit": "count",
    "color": "23/a",
}

metric_info['epoch_objects'] = {
    "title": _("Epoch objects"),
    "unit": "count",
    "color": "42/a",
}

metric_info['graylog_input'] = {
    "title": _("Input traffic"),
    "unit": "bytes",
    "color": "16/b",
}

metric_info['graylog_output'] = {
    "title": _("Output traffic"),
    "unit": "bytes",
    "color": "23/a",
}

metric_info['graylog_decoded'] = {
    "title": _("Decoded traffic"),
    "unit": "bytes",
    "color": "42/a",
}

metric_info['graylog_diff'] = {
    "title": _("Number of messages in defined timespan"),
    "unit": "count",
    "color": "11/a",
}

metric_info["collectors_running"] = {
    "title": _("Running collectors"),
    "unit": "count",
    "color": "26/a",
}
metric_info["collectors_stopped"] = {
    "title": _("Stopped collectors"),
    "unit": "count",
    "color": "21/a",
}
metric_info["collectors_failing"] = {
    "title": _("Failing collectors"),
    "unit": "count",
    "color": "12/a",
}

metric_info["num_streams"] = {
    "title": _("Streams"),
    "unit": "count",
    "color": "11/a",
}

metric_info["item_memory"] = {
    "color": "26/a",
    "title": _("Item memory"),
    "unit": "bytes",
}

metric_info["resident_items_ratio"] = {
    "title": _("Resident items ratio"),
    "unit": "%",
    "color": "23/a",
}

metric_info["fetched_items"] = {
    "title": _("Number of fetched items"),
    "unit": "count",
    "color": "23/b",
}

metric_info['jira_count'] = {
    "title": _("Number of issues"),
    "unit": "count",
    "color": "14/a",
}

metric_info['jira_sum'] = {
    "title": _("Result of summed up values"),
    "unit": "count",
    "color": "14/a",
}

metric_info['jira_avg'] = {
    "title": _("Average value"),
    "unit": "count",
    "color": "14/a",
}

metric_info['jira_diff'] = {
    "title": _("Difference"),
    "unit": "count",
    "color": "11/a",
}

metric_info['consumers'] = {
    "title": _("Consumers"),
    "unit": "count",
    "color": "21/a",
}

metric_info['exchanges'] = {
    "title": _("Exchanges"),
    "unit": "count",
    "color": "26/a",
}

metric_info['queues'] = {
    "title": _("Queues"),
    "unit": "count",
    "color": "31/a",
}

metric_info['messages_rate'] = {
    "title": _("Message Rate"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info['messages_ready'] = {
    "title": _("Ready messages"),
    "unit": "count",
    "color": "11/a",
}

metric_info['messages_unacknowledged'] = {
    "title": _("Unacknowledged messages"),
    "unit": "count",
    "color": "14/a",
}

metric_info['messages_publish'] = {
    "title": _("Published messages"),
    "unit": "count",
    "color": "31/a",
}

metric_info['messages_publish_rate'] = {
    "title": _("Published message rate"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info['messages_deliver'] = {
    "title": _("Delivered messages"),
    "unit": "count",
    "color": "26/a",
}

metric_info['messages_deliver_rate'] = {
    "title": _("Delivered message rate"),
    "unit": "1/s",
    "color": "53/a",
}

metric_info['gc_runs'] = {
    "title": _("GC runs"),
    "unit": "count",
    "color": "31/a",
}

metric_info['gc_runs_rate'] = {
    "title": _("GC runs rate"),
    "unit": "1/s",
    "color": "53/a",
}

metric_info['runtime_run_queue'] = {
    "title": _("Runtime run queue"),
    "unit": "count",
    "color": "21/a",
}

metric_info['gc_bytes'] = {
    "title": _("Bytes reclaimed by GC"),
    "unit": "bytes",
    "color": "32/a",
}

metric_info['gc_bytes_rate'] = {
    "title": _("Bytes reclaimed by GC rate"),
    "unit": "bytes/s",
    "color": "42/a",
}

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

graph_info["replicas"] = {
    "title": _("Replicas"),
    "metrics": [
        ("ready_replicas", "area"),
        ("total_replicas", "line"),
    ],
    "scalars": ["ready_replicas:crit",]
}

# TODO: Warum ist hier überall line? Default ist Area.
# Kann man die hit ratios nicht schön stacken? Ist
# nicht total die Summe der anderen?

graph_info["bufferpool_hitratios"] = {
    "title": _("Bufferpool Hitratios"),
    "metrics": [
        ("total_hitratio", "line"),
        ("data_hitratio", "line"),
        ("index_hitratio", "line"),
        ("xda_hitratio", "line"),
    ],
}

graph_info["deadlocks_and_waits"] = {
    "title": _("Dead- and waitlocks"),
    "metrics": [
        ("deadlocks", "area"),
        ("lockwaits", "stack"),
    ],
}

graph_info["licenses"] = {
    "title": _("Licenses"),
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
    "title": _("Number of signed-in users"),
    "metrics": [("current_users", "area"),],
    "scalars": [
        "current_users:warn",
        "current_users:crit",
    ],
}
