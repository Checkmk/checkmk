#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.render

from cmk.gui.i18n import _
from cmk.gui.plugins.metrics.utils import (
    graph_info,
    indexed_color,
    MAX_NUMBER_HOPS,
    metric_info,
    parse_color_into_hexrgb,
)

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


def register_hop_metrics():
    for idx in range(0, MAX_NUMBER_HOPS):
        if idx:
            prefix_perf = "hop_%d_" % idx
            prefix_text = "Hop %d " % idx
        else:
            prefix_perf = ""
            prefix_text = ""

        metric_info["%srta" % prefix_perf] = {
            "title": _("%sRound trip average") % prefix_text,
            "unit": "s",
            "color": "33/a",
        }

        metric_info["%srtmin" % prefix_perf] = {
            "title": _("%sRound trip minimum") % prefix_text,
            "unit": "s",
            "color": "42/a",
        }

        metric_info["%srtmax" % prefix_perf] = {
            "title": _("%sRound trip maximum") % prefix_text,
            "unit": "s",
            "color": "42/b",
        }

        metric_info["%srtstddev" % prefix_perf] = {
            "title": _("%sRound trip standard devation") % prefix_text,
            "unit": "s",
            "color": "16/a",
        }

        metric_info["%spl" % prefix_perf] = {
            "title": _("%sPacket loss") % prefix_text,
            "unit": "%",
            "color": "#ffc030",
        }

        metric_info["%sresponse_time" % prefix_perf] = {
            "title": _("%sResponse time") % prefix_text,
            "unit": "s",
            "color": "23/a",
        }


register_hop_metrics()

metric_info["accepted"] = {
    "title": _("Accepted connections"),
    "unit": "count",
    "color": "11/a",
}

metric_info["accepted_per_sec"] = {
    "title": _("Accepted connections per second"),
    "unit": "1/s",
    "color": "16/a",
}

metric_info["handled"] = {
    "title": _("Handled connections"),
    "unit": "count",
    "color": "21/a",
}

metric_info["handled_per_sec"] = {
    "title": _("Handled connections per second"),
    "unit": "1/s",
    "color": "26/a",
}

metric_info["requests"] = {
    "title": _("Requests per second"),
    "unit": "count",
    "color": "31/a",
}

metric_info["requests_per_conn"] = {
    "title": _("Requests per connection"),
    "unit": "count",
    "color": "33/a",
}

metric_info["requests_per_sec"] = {
    "title": _("Requests per second"),
    "unit": "1/s",
    "color": "36/a",
}

metric_info["active"] = {
    "title": _("Active connections"),
    "unit": "count",
    "color": "11/a",
}

metric_info["reading"] = {
    "title": _("Reading connections"),
    "unit": "count",
    "color": "16/a",
}

metric_info["waiting"] = {
    "title": _("Waiting connections"),
    "unit": "count",
    "color": "21/a",
}

metric_info["writing"] = {
    "title": _("Writing connections"),
    "unit": "count",
    "color": "21/a",
}

metric_info["apply_finish_time"] = {
    "title": _("Apply Finish Time"),
    "unit": "s",
    "color": "11/a",
}

metric_info["transport_lag"] = {
    "title": _("Transport Lag"),
    "unit": "s",
    "color": "16/a",
}

metric_info["apply_lag"] = {
    "title": _("Apply Lag"),
    "unit": "s",
    "color": "21/a",
}

metric_info["rtt"] = {
    "title": _("Round trip time"),
    "unit": "s",
    "color": "33/a",
}

metric_info["hops"] = {
    "title": _("Number of hops"),
    "unit": "count",
    "color": "51/a",
}

metric_info["uptime"] = {
    "title": _("Uptime"),
    "unit": "s",
    "color": "#80f000",
}

metric_info["time_difference"] = {
    "title": _("Time difference"),
    "unit": "s",
    "color": "#80f000",
}

metric_info["transactions"] = {
    "title": _("Transaction count"),
    "unit": "count",
    "color": "36/a",
}

metric_info["server_latency"] = {
    "title": _("Server latency"),
    "unit": "s",
    "color": "21/a",
}

metric_info["e2e_latency"] = {
    "title": _("End-to-end latency"),
    "unit": "s",
    "color": "21/b",
}

metric_info["availability"] = {
    "title": _("Availability"),
    "unit": "%",
    "color": "31",
}

# TODO: Metric names with preceeding numbers seems not to be capable
# of adding scalars with graph_info (e.g. for horizontal warning levels)
metric_info["5ghz_clients"] = {
    "title": _("Client connects for 5 Ghz Band"),
    "unit": "count",
    "color": "13/a",
}

metric_info["24ghz_clients"] = {
    "title": _("Client connects for 2,4 Ghz Band"),
    "unit": "count",
    "color": "14/a",
}

metric_info["cifs_share_users"] = {
    "title": _("Users using a cifs share"),
    "unit": "count",
    "color": "#60f020",
}

metric_info["time_offset"] = {
    "title": _("Time offset"),
    "unit": "s",
    "color": "#9a52bf",
}

metric_info["jitter"] = {
    "title": _("Time dispersion (jitter)"),
    "unit": "s",
    "color": "43/b",
}

metric_info["connection_time"] = {
    "title": _("Connection time"),
    "unit": "s",
    "color": "#94b65a",
}

metric_info["infections_rate"] = {
    "title": _("Infections"),
    "unit": "1/s",
    "color": "15/a",
}

metric_info["connections_blocked_rate"] = {
    "title": _("Blocked connections"),
    "unit": "1/s",
    "color": "14/a",
}

metric_info["connections_failed_rate"] = {
    "title": _("Failed connections"),
    "unit": "1/s",
    "color": "14/a",
}

metric_info["open_network_sockets"] = {
    "title": _("Open network sockets"),
    "unit": "count",
    "color": "21/a",
}

metric_info["connections"] = {
    "title": _("Connections"),
    "unit": "count",
    "color": "#a080b0",
}

metric_info["idle_connections"] = {
    "title": _("Idle connections"),
    "unit": "count",
    "color": "#a080f0",
}

metric_info["active_connections"] = {
    "title": _("Active connections"),
    "unit": "count",
    "color": "#a020c0",
}

metric_info["connections_ssl"] = {
    "title": _("SSL connections"),
    "unit": "count",
    "color": "13/a",
}

metric_info["connections_ssl_vpn"] = {
    "title": _("SSL/VPN connections"),
    "unit": "count",
    "color": "13/a",
}

metric_info["connections_async_writing"] = {
    "title": _("Asynchronous writing connections"),
    "unit": "count",
    "color": "16/a",
}

metric_info["connections_async_keepalive"] = {
    "title": _("Asynchronous keep alive connections"),
    "unit": "count",
    "color": "22/a",
}

metric_info["connections_async_closing"] = {
    "title": _("Asynchronous closing connections"),
    "unit": "count",
    "color": "24/a",
}

metric_info["connections_rate"] = {
    "title": _("Connections per second"),
    "unit": "1/s",
    "color": "#a080b0",
}

metric_info["connections_duration_min"] = {
    "title": _("Connections duration min"),
    "unit": "s",
    "color": "24/a",
}

metric_info["connections_duration_max"] = {
    "title": _("Connections duration max"),
    "unit": "s",
    "color": "25/a",
}

metric_info["connections_duration_mean"] = {
    "title": _("Connections duration mean"),
    "unit": "s",
    "color": "25/a",
}

metric_info["packet_velocity_asic"] = {
    "title": _("Packet velocity asic"),
    "unit": "1/s",
    "color": "26/a",
}

metric_info["requests_per_second"] = {
    "title": _("Requests per second"),
    "unit": "1/s",
    "color": "#4080a0",
}

metric_info["busy_workers"] = {
    "title": _("Busy workers"),
    "unit": "count",
    "color": "#a080b0",
}

metric_info["idle_workers"] = {
    "title": _("Idle workers"),
    "unit": "count",
    "color": "43/b",
}

metric_info["busy_servers"] = {
    "title": _("Busy servers"),
    "unit": "count",
    "color": "#a080b0",
}

metric_info["idle_servers"] = {
    "title": _("Idle servers"),
    "unit": "count",
    "color": "43/b",
}

metric_info["open_slots"] = {
    "title": _("Open slots"),
    "unit": "count",
    "color": "31/a",
}

metric_info["total_slots"] = {
    "title": _("Total slots"),
    "unit": "count",
    "color": "33/b",
}

metric_info["total_sessions"] = {
    "title": _("Total sessions"),
    "unit": "count",
    "color": "#94b65a",
}

metric_info["running_sessions"] = {
    "title": _("Running sessions"),
    "unit": "count",
    "color": "42/a",
}

metric_info["rejected_sessions"] = {
    "title": _("Rejected sessions"),
    "unit": "count",
    "color": "45/a",
}

metric_info["active_sessions"] = {
    "title": _("Active sessions"),
    "unit": "count",
    "color": "11/a",
}

metric_info["active_sessions_peak"] = {
    "title": _("Peak value of active sessions"),
    "unit": "count",
    "color": "#000000",
}

metric_info["inactive_sessions"] = {
    "title": _("Inactive sessions"),
    "unit": "count",
    "color": "13/a",
}

metric_info["session_rate"] = {
    "title": _("Session Rate"),
    "unit": "1/s",
    "color": "#4080a0",
}

metric_info["children_user_time"] = {
    "title": _("Child time in user space"),
    "unit": "s",
    "color": "#aef090",
}

metric_info["children_system_time"] = {
    "title": _("Child time in system space"),
    "unit": "s",
    "color": "#ffb080",
}

metric_info["sync_latency"] = {
    "title": _("Sync latency"),
    "unit": "s",
    "color": "#ffb080",
}

metric_info["relay_log_space"] = {
    "title": _("Relay Log Size"),
    "unit": "bytes",
    "color": "#ffb080",
}

metric_info["mail_latency"] = {
    "title": _("Mail latency"),
    "unit": "s",
    "color": "#ffb080",
}

metric_info["p2s_bandwidth"] = {
    "title": _("Point-to-site bandwidth"),
    "unit": "bytes/s",
    "color": "#00c0ff",
}

metric_info["s2s_bandwidth"] = {
    "title": _("Site-to-site bandwidth"),
    "unit": "bytes/s",
    "color": "#00c080",
}

# “Output Queue Length is the length of the output packet queue (in
# packets). If this is longer than two, there are delays and the bottleneck
# should be found and eliminated, if possible.
metric_info["outqlen"] = {
    "title": _("Length of output queue"),
    "unit": "count",
    "color": "25/a",
}

metric_info["wlan_physical_errors"] = {
    "title": "WLAN physical errors",
    "unit": "1/s",
    "color": "14/a",
}

metric_info["wlan_resets"] = {
    "title": "WLAN Reset operations",
    "unit": "1/s",
    "color": "21/a",
}

metric_info["wlan_retries"] = {
    "title": "WLAN transmission retries",
    "unit": "1/s",
    "color": "24/a",
}

metric_info["broadcast_packets"] = {
    "title": _("Broadcast packets"),
    "unit": "1/s",
    "color": "11/a",
}

metric_info["multicast_packets"] = {
    "title": _("Multicast packets"),
    "unit": "1/s",
    "color": "14/a",
}

metric_info["tcp_listen"] = {
    "title": _("State %s") % "LISTEN",
    "unit": "count",
    "color": "44/a",
}

metric_info["tcp_established"] = {
    "title": _("State %s") % "ESTABLISHED",
    "unit": "count",
    "color": "#00f040",
}

metric_info["tcp_syn_sent"] = {
    "title": _("State %s") % "SYN_SENT",
    "unit": "count",
    "color": "#a00000",
}

metric_info["tcp_syn_recv"] = {
    "title": _("State %s") % "SYN_RECV",
    "unit": "count",
    "color": "#ff4000",
}

metric_info["tcp_last_ack"] = {
    "title": _("State %s") % "LAST_ACK",
    "unit": "count",
    "color": "#c060ff",
}

metric_info["tcp_close_wait"] = {
    "title": _("State %s") % "CLOSE_WAIT",
    "unit": "count",
    "color": "#f000f0",
}

metric_info["tcp_time_wait"] = {
    "title": _("State %s") % "TIME_WAIT",
    "unit": "count",
    "color": "#00b0b0",
}

metric_info["tcp_closed"] = {
    "title": _("State %s") % "CLOSED",
    "unit": "count",
    "color": "#ffc000",
}

metric_info["tcp_closing"] = {
    "title": _("State %s") % "CLOSING",
    "unit": "count",
    "color": "#ffc080",
}

metric_info["tcp_fin_wait1"] = {
    "title": _("State %s") % "FIN_WAIT1",
    "unit": "count",
    "color": "#cccccc",
}

metric_info["tcp_fin_wait2"] = {
    "title": _("State %s") % "FIN_WAIT2",
    "unit": "count",
    "color": "#888888",
}

metric_info["tcp_bound"] = {
    "title": _("State %s") % "BOUND",
    "unit": "count",
    "color": "#4060a0",
}

metric_info["tcp_idle"] = {
    "title": _("State %s") % "IDLE",
    "unit": "count",
    "color": "41/a",
}

metric_info["fw_connections_active"] = {
    "title": _("Active connections"),
    "unit": "count",
    "color": "15/a",
}

metric_info["fw_connections_established"] = {
    "title": _("Established connections"),
    "unit": "count",
    "color": "41/a",
}

metric_info["fw_connections_halfopened"] = {
    "title": _("Half opened connections"),
    "unit": "count",
    "color": "16/a",
}

metric_info["fw_connections_halfclosed"] = {
    "title": _("Half closed connections"),
    "unit": "count",
    "color": "11/a",
}

metric_info["fw_connections_passthrough"] = {
    "title": _("Unoptimized connections"),
    "unit": "count",
    "color": "34/a",
}

metric_info["average_message_rate"] = {
    "title": _("Incoming messages"),
    "unit": "1/s",
    "color": "23/a",
}

metric_info["average_drop_rate"] = {
    "title": _("Dropped messages"),
    "unit": "1/s",
    "color": "21/b",
}

metric_info["average_sync_time"] = {
    "title": _("Average slave sync time"),
    "unit": "s",
    "color": "46/a",
}

metric_info["average_rule_trie_rate"] = {
    "title": _("Rule tries"),
    "unit": "1/s",
    "color": "33/a",
}

metric_info["average_rule_hit_rate"] = {
    "title": _("Rule hits"),
    "unit": "1/s",
    "color": "34/b",
}

metric_info["average_event_rate"] = {
    "title": _("Event creations"),
    "unit": "1/s",
    "color": "31/a",
}

metric_info["average_connect_rate"] = {
    "title": _("Client connects"),
    "unit": "1/s",
    "color": "15/a",
}

metric_info["average_request_time"] = {
    "title": _("Average request response time"),
    "unit": "s",
    "color": "14/a",
}

metric_info["average_processing_time"] = {
    "title": _("Event processing time"),
    "unit": "s",
    "color": "13/a",
}

metric_info["average_rule_hit_ratio"] = {
    "title": _("Rule hit ratio"),
    "unit": "%",
    "color": "#cccccc",
}

metric_info["used_dhcp_leases"] = {
    "title": _("Used DHCP leases"),
    "unit": "count",
    "color": "#60bbbb",
}

metric_info["free_dhcp_leases"] = {
    "title": _("Free DHCP leases"),
    "unit": "count",
    "color": "34/a",
}

metric_info["pending_dhcp_leases"] = {
    "title": _("Pending DHCP leases"),
    "unit": "count",
    "color": "31/a",
}

metric_info["net_data_recv"] = {
    "title": _("Net data received"),
    "unit": "bytes/s",
    "color": "41/b",
}

metric_info["net_data_sent"] = {
    "title": _("Net data sent"),
    "unit": "bytes/s",
    "color": "42/a",
}

metric_info["total_modems"] = {
    "title": _("Total number of modems"),
    "unit": "count",
    "color": "12/c",
}

metric_info["active_modems"] = {
    "title": _("Active modems"),
    "unit": "count",
    "color": "14/c",
}

metric_info["registered_modems"] = {
    "title": _("Registered modems"),
    "unit": "count",
    "color": "16/c",
}

metric_info["channel_utilization"] = {
    "title": _("Channel utilization"),
    "unit": "%",
    "color": "24/c",
}

metric_info["channel_utilization_24ghz"] = {
    "title": _("Channel utilization for 2,4GHz Band"),
    "unit": "%",
    "color": "25/c",
}

metric_info["channel_utilization_5ghz"] = {
    "title": _("Channel utilization for 5GHz Band"),
    "unit": "%",
    "color": "26/c",
}

metric_info["connector_outlets"] = {
    "title": _("Connector outlets"),
    "unit": "count",
    "color": "51/a",
}

metric_info["response_size"] = {
    "title": _("Response size"),
    "unit": "bytes",
    "color": "53/b",
}

metric_info["time_connect"] = {
    "title": _("Time to connect"),
    "unit": "s",
    "color": "11/a",
}

metric_info["time_ssl"] = {
    "title": _("Time to negotiate SSL"),
    "unit": "s",
    "color": "13/a",
}

metric_info["time_headers"] = {
    "title": _("Time to send request"),
    "unit": "s",
    "color": "15/a",
}

metric_info["time_firstbyte"] = {
    "title": _("Time to receive start of response"),
    "unit": "s",
    "color": "26/a",
}

metric_info["time_transfer"] = {
    "title": _("Time to receive full response"),
    "unit": "s",
    "color": "41/a",
}

metric_info["ap_devices_total"] = {
    "title": _("Total devices"),
    "unit": "count",
    "color": "51/a",
}

metric_info["ap_devices_drifted"] = {
    "title": _("Time drifted devices"),
    "unit": "count",
    "color": "23/a",
}

metric_info["ap_devices_not_responding"] = {
    "title": _("Not responding devices"),
    "unit": "count",
    "color": "14/a",
}

for ctype, ccolor in (
    ("critical", "14/a"),
    ("minor", "23/b"),
    ("cleared", "32/b"),
):
    metric_info["ap_devices_" + ctype] = {
        "title": ctype.title(),
        "unit": "count",
        "color": ccolor,
    }

for ctype, ccolor in (
    ("dot11a", "21/a"),
    ("dot11b", "21/b"),
    ("dot11g", "33/a"),
    ("dot11ac", "34/b"),
    ("dot11n2_4", "45/a"),
    ("dot11n5", "46/b"),
):
    metric_info["wifi_connection_" + ctype] = {
        "title": "802." + ctype,
        "unit": "count",
        "color": ccolor,
    }

metric_info["wifi_connection_total"] = {
    "title": "Total connections",
    "unit": "count",
    "color": "35/a",
}

metric_info["ap_devices_percent_unhealthy"] = {
    "title": "Percentage of unhealthy access points",
    "unit": "%",
    "color": "33/a",
}

metric_info["request_rate"] = {
    "title": _("Request rate"),
    "unit": "1/s",
    "color": "34/a",
}

metric_info["error_rate"] = {
    "title": _("Error rate"),
    "unit": "1/s",
    "color": "14/a",
}

metric_info["managed_object_count"] = {
    "title": _("Managed Objects"),
    "unit": "count",
    "color": "45/a",
}

metric_info["active_vpn_tunnels"] = {
    "title": _("Active VPN Tunnels"),
    "unit": "count",
    "color": "43/a",
}

metric_info["active_vpn_users"] = {
    "title": _("Active VPN Users"),
    "unit": "count",
    "color": "23/a",
}

metric_info["active_vpn_websessions"] = {
    "title": _("Active VPN Web Sessions"),
    "unit": "count",
    "color": "33/a",
}

metric_info["current_users"] = {
    "title": _("Current Users"),
    "unit": "count",
    "color": "23/a",
}

metric_info["average_latency"] = {
    "title": _("Average Latency"),
    "unit": "s",
    "color": "35/a",
}

metric_info["total_active_sessions"] = {
    "title": _("Total Active Sessions"),
    "unit": "count",
    "color": "#888888",
}

metric_info["tcp_active_sessions"] = {
    "title": _("Active TCP Sessions"),
    "unit": "count",
    "color": "#888800",
}

metric_info["udp_active_sessions"] = {
    "title": _("Active UDP sessions"),
    "unit": "count",
    "color": "#880088",
}

metric_info["icmp_active_sessions"] = {
    "title": _("Active ICMP Sessions"),
    "unit": "count",
    "color": "#008888",
}

metric_info["packages_accepted"] = {
    "title": _("Accepted Packages/s"),
    "unit": "1/s",
    "color": "#80ff40",
}
metric_info["packages_blocked"] = {
    "title": _("Blocked Packages/s"),
    "unit": "1/s",
    "color": "14/a",
}

metric_info["packages_icmp_total"] = {
    "title": _("ICMP Packages/s"),
    "unit": "count",
    "color": "21/a",
}

metric_info["sslproxy_active_sessions"] = {
    "title": _("Active SSL Proxy sessions"),
    "unit": "count",
    "color": "#11FF11",
}

metric_info["locks_per_batch"] = {
    "title": _("Locks/Batch"),
    "unit": "",
    "color": "21/a",
}

metric_info["page_reads_sec"] = {
    "title": _("Page Reads"),
    "unit": "1/s",
    "color": "33/b",
}

metric_info["page_writes_sec"] = {
    "title": _("Page Writes"),
    "unit": "1/s",
    "color": "14/a",
}

metric_info["page_lookups_sec"] = {
    "title": _("Page Lookups"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["failed_search_requests"] = {
    "title": _("WEB - Failed search requests"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["failed_location_requests"] = {
    "title": _("WEB - Failed Get Locations Requests"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["failed_ad_requests"] = {
    "title": _("WEB - Timed out Active Directory Requests"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["http_5xx"] = {
    "title": _("HTTP 500 errors"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["sip_message_processing_time"] = {
    "title": _("SIP - Average Incoming Message Processing Time"),
    "unit": "s",
    "color": "42/a",
}

metric_info["asp_requests_rejected"] = {
    "title": _("ASP Requests Rejected"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["failed_file_requests"] = {
    "title": _("Failed File Requests"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["join_failures"] = {
    "title": _("Join Launcher Service Failures"),
    "unit": "count",
    "color": "42/a",
}

metric_info["failed_validate_cert_calls"] = {
    "title": _("WEB - Failed validate cert calls"),
    "unit": "count",
    "color": "42/a",
}

metric_info["sip_incoming_responses_dropped"] = {
    "title": _("SIP - Incoming Responses Dropped"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["sip_incoming_requests_dropped"] = {
    "title": _("SIP - Incoming Requests Dropped"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["usrv_queue_latency"] = {
    "title": _("USrv - Queue Latency"),
    "unit": "s",
    "color": "42/a",
}

metric_info["usrv_sproc_latency"] = {
    "title": _("USrv - Sproc Latency"),
    "unit": "s",
    "color": "42/a",
}

metric_info["usrv_throttled_requests"] = {
    "title": _("USrv - Throttled requests"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["sip_503_responses"] = {
    "title": _("SIP - Local 503 Responses"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["sip_incoming_messages_timed_out"] = {
    "title": _("SIP - Incoming Messages Timed out"),
    "unit": "count",
    "color": "42/a",
}

metric_info["caa_incomplete_calls"] = {
    "title": _("CAA - Incomplete Calls"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["usrv_create_conference_latency"] = {
    "title": _("USrv - Create Conference Latency"),
    "unit": "s",
    "color": "42/a",
}

metric_info["usrv_allocation_latency"] = {
    "title": _("USrv - Allocation Latency"),
    "unit": "s",
    "color": "42/a",
}

metric_info["sip_avg_holding_time_incoming_messages"] = {
    "title": _("SIP - Average Holding Time For Incoming Messages"),
    "unit": "s",
    "color": "42/a",
}

metric_info["sip_flow_controlled_connections"] = {
    "title": _("SIP - Flow-controlled Connections"),
    "unit": "count",
    "color": "42/a",
}

metric_info["sip_avg_outgoing_queue_delay"] = {
    "title": _("SIP - Average Outgoing Queue Delay"),
    "unit": "s",
    "color": "42/a",
}

metric_info["sip_sends_timed_out"] = {
    "title": _("SIP - Sends Timed-Out"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["sip_authentication_errors"] = {
    "title": _("SIP - Authentication Errors"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["mediation_load_call_failure_index"] = {
    "title": _("MediationServer - Load Call Failure Index"),
    "unit": "count",
    "color": "42/a",
}

metric_info["mediation_failed_calls_because_of_proxy"] = {
    "title": _("MediationServer - Failed calls caused by unexpected interaction from proxy"),
    "unit": "count",
    "color": "42/a",
}

metric_info["mediation_failed_calls_because_of_gateway"] = {
    "title": _("MediationServer - Failed calls caused by unexpected interaction from gateway"),
    "unit": "count",
    "color": "42/a",
}

metric_info["mediation_media_connectivity_failure"] = {
    "title": _("Mediation Server - Media Connectivity Check Failure"),
    "unit": "count",
    "color": "42/a",
}

metric_info["avauth_failed_requests"] = {
    "title": _("A/V Auth - Bad Requests Received"),
    "unit": "count",
    "color": "42/a",
}

metric_info["edge_udp_failed_auth"] = {
    "title": _("UDP Authentication Failures"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["edge_tcp_failed_auth"] = {
    "title": _("A/V Edge - TCP Authentication Failures"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["edge_udp_allocate_requests_exceeding_port_limit"] = {
    "title": _("A/V Edge - UDP Allocate Requests Exceeding Port Limit"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["edge_tcp_allocate_requests_exceeding_port_limit"] = {
    "title": _("A/V Edge - TCP Allocate Requests Exceeding Port Limit"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["edge_udp_packets_dropped"] = {
    "title": _("A/V Edge - UDP Packets Dropped"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["edge_tcp_packets_dropped"] = {
    "title": _("A/V Edge - TCP Packets Dropped"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["tcp_packets_received"] = {
    "title": _("Received TCP packets"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["udp_packets_received"] = {
    "title": _("Received UDP packets"),
    "unit": "1/s",
    "color": "23/a",
}

metric_info["icmp_packets_received"] = {
    "title": _("Received ICMP packets"),
    "unit": "1/s",
    "color": "25/a",
}

metric_info["dataproxy_connections_throttled"] = {
    "title": _("DATAPROXY - Throttled Server Connections"),
    "unit": "count",
    "color": "42/a",
}

metric_info["xmpp_failed_outbound_streams"] = {
    "title": _("XmppFederationProxy - Failed outbound stream establishes"),
    "unit": "1/s",
    "color": "26/a",
}

metric_info["xmpp_failed_inbound_streams"] = {
    "title": _("XmppFederationProxy - Failed inbound stream establishes"),
    "unit": "1/s",
    "color": "31/a",
}

metric_info["web_requests_processing"] = {
    "title": _("WEB - Requests in Processing"),
    "unit": "count",
    "color": "12/a",
}

metric_info["dhcp_discovery"] = {
    "title": _("DHCP Discovery messages"),
    "unit": "count",
    "color": "11/a",
}

metric_info["dhcp_requests"] = {
    "title": _("DHCP received requests"),
    "unit": "count",
    "color": "14/a",
}

metric_info["dhcp_releases"] = {
    "title": _("DHCP received releases"),
    "unit": "count",
    "color": "21/a",
}

metric_info["dhcp_declines"] = {
    "title": _("DHCP received declines"),
    "unit": "count",
    "color": "24/a",
}

metric_info["dhcp_informs"] = {
    "title": _("DHCP received informs"),
    "unit": "count",
    "color": "31/a",
}

metric_info["dhcp_others"] = {
    "title": _("DHCP received other messages"),
    "unit": "count",
    "color": "34/a",
}

metric_info["dhcp_offers"] = {
    "title": _("DHCP sent offers"),
    "unit": "count",
    "color": "12/a",
}

metric_info["dhcp_acks"] = {
    "title": _("DHCP sent acks"),
    "unit": "count",
    "color": "15/a",
}

metric_info["dhcp_nacks"] = {
    "title": _("DHCP sent nacks"),
    "unit": "count",
    "color": "22/b",
}

metric_info["dns_successes"] = {
    "title": _("DNS successful responses"),
    "unit": "count",
    "color": "11/a",
}

metric_info["dns_referrals"] = {
    "title": _("DNS referrals"),
    "unit": "count",
    "color": "14/a",
}

metric_info["dns_recursion"] = {
    "title": _("DNS queries received using recursion"),
    "unit": "count",
    "color": "21/a",
}

metric_info["dns_failures"] = {
    "title": _("DNS failed queries"),
    "unit": "count",
    "color": "24/a",
}

metric_info["dns_nxrrset"] = {
    "title": _("DNS queries received for non-existent record"),
    "unit": "count",
    "color": "31/a",
}

metric_info["dns_nxdomain"] = {
    "title": _("DNS queries received for non-existent domain"),
    "unit": "count",
    "color": "34/a",
}

metric_info["inside_macs"] = {
    "title": _("Number of unique inside MAC addresses"),
    "unit": "count",
    "color": "31/a",
}

metric_info["outside_macs"] = {
    "title": _("Number of unique outside MAC addresses"),
    "unit": "count",
    "color": "33/a",
}

metric_info["queue"] = {
    "title": _("Queue length"),
    "unit": "count",
    "color": "42/a",
}

metric_info["avg_response_time"] = {
    "title": _("Average response time"),
    "unit": "s",
    "color": "#4040ff",
}

metric_info["remaining_reads"] = {
    "title": _("Remaining Reads"),
    "unit": "count",
    "color": "42/a",
}

metric_info["dtu_percent"] = {
    "title": _("Database throughput unit"),
    "unit": "%",
    "color": "#4040ff",
}

metric_info["connections_max_used"] = {
    "title": _("Maximum used parallel connections"),
    "unit": "count",
    "color": "42/a",
}

metric_info["connections_max"] = {
    "title": _("Maximum parallel connections"),
    "unit": "count",
    "color": "51/b",
}

metric_info["connections_conn_threads"] = {
    "title": _("Currently open connections"),
    "unit": "count",
    "color": "31/c",
}

metric_info["connections_perc_conn_threads"] = {
    "title": _("Open connections load"),
    "unit": "%",
    "color": "31/c",
}

metric_info["connections_perc_used"] = {
    "title": _("Parallel connections load"),
    "unit": "%",
    "color": "42/a",
}

metric_info["op_s"] = {
    "title": _("Operations per second"),
    "unit": "count",
    "color": "#90ee90",
}

metric_info["rpc_backlog"] = {
    "title": _("RPC Backlog"),
    "unit": "count",
    "color": "#90ee90",
}

metric_info["read_ops"] = {
    "title": _("Read operations"),
    "unit": "1/s",
    "color": "34/a",
}

metric_info["read_b_s"] = {
    "title": _("Read size per second"),
    "unit": "bytes/s",
    "color": "#80ff20",
}

metric_info["read_b_op"] = {
    "title": _("Read size per operation"),
    "unit": "bytes/op",
    "color": "#4080c0",
    "render": lambda value: cmk.utils.render.fmt_bytes(int(value)),
}

metric_info["read_retrans"] = {
    "title": _("Read retransmission"),
    "unit": "%",
    "color": "#90ee90",
}

metric_info["read_avg_rtt_ms"] = {
    "title": _("Read average rtt"),
    "unit": "s",
    "color": "#90ee90",
}

metric_info["read_avg_exe_ms"] = {
    "title": _("Read average exe"),
    "unit": "s",
    "color": "#90ee90",
}

metric_info["write_ops_s"] = {
    "title": _("Write operations"),
    "unit": "1/s",
    "color": "34/a",
}

metric_info["write_b_s"] = {
    "title": _("Writes size per second"),
    "unit": "bytes/s",
    "color": "#80ff20",
}

metric_info["write_b_op"] = {
    "title": _("Writes size per operation"),
    "unit": "bytes/op",
    "color": "#4080c0",
    "render": lambda value: cmk.utils.render.fmt_bytes(int(value)),
}

metric_info["write_avg_rtt_ms"] = {
    "title": _("Write average rtt"),
    "unit": "s",
    "color": "#90ee90",
}

metric_info["write_avg_exe_ms"] = {
    "title": _("Write average exe"),
    "unit": "s",
    "color": "#90ee90",
}


def register_requests_metrics() -> None:
    for request, color in zip(
        ["get", "put", "delete", "head", "post", "select", "list"],
        ["11/a", "13/a", "15/a", "21/a", "23/a", "25/a", "31/a"],
    ):
        metric_info["%s_requests" % request] = {
            "title": _("%s Requests") % request.upper(),
            "unit": "1/s",
            "color": color,
        }
        metric_info["%s_requests_perc" % request] = {
            "title": _("Percentage %s Requests") % request.upper(),
            "unit": "%",
            "color": color,
        }


register_requests_metrics()

metric_info["channels"] = {
    "title": _("Channels"),
    "unit": "count",
    "color": "11/a",
}

metric_info["bytes_accepted"] = {
    "title": _("Bytes accepted"),
    "unit": "bytes/s",
    "color": "21/a",
}

metric_info["bytes_dropped"] = {
    "title": _("Bytes dropped"),
    "unit": "bytes/s",
    "color": "32/a",
}

metric_info["bytes_rejected"] = {
    "title": _("Bytes rejected"),
    "unit": "bytes/s",
    "color": "42/a",
}

metric_info["packets"] = {
    "title": _("Total number of packets"),
    "unit": "1/s",
    "color": "11/a",
}

metric_info["packets_accepted"] = {
    "title": _("Packets accepted"),
    "unit": "1/s",
    "color": "21/a",
}

metric_info["packets_dropped"] = {
    "title": _("Packets dropped"),
    "unit": "1/s",
    "color": "32/a",
}

metric_info["packets_rejected"] = {
    "title": _("Packets rejected"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["fortiauthenticator_fails_5min"] = {
    "title": _("Authentication failures (last 5 minutes)"),
    "unit": "count",
    "color": "42/a",
}

metric_info["fortigate_detection_rate"] = {
    "title": _("Detection rate"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["fortigate_blocking_rate"] = {
    "title": _("Blocking rate"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["ap_count"] = {
    "title": _("Number of access points"),
    "unit": "count",
    "color": "11/a",
}

metric_info["clients_count"] = {
    "title": _("Number of clients"),
    "unit": "count",
    "color": "22/a",
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

# Networking

graph_info["bandwidth_translated"] = {
    "title": _("Bandwidth"),
    "metrics": [
        ("if_in_octets,8,*@bits/s", "area", _("Input bandwidth")),
        ("if_out_octets,8,*@bits/s", "-area", _("Output bandwidth")),
    ],
    "scalars": [
        ("if_in_octets:warn", _("Warning (In)")),
        ("if_in_octets:crit", _("Critical (In)")),
        ("if_out_octets:warn,-1,*", _("Warning (Out)")),
        ("if_out_octets:crit,-1,*", _("Critical (Out)")),
    ],
}

# Same but for checks that have been translated in to bits/s
graph_info["bandwidth"] = {
    "title": _("Bandwidth"),
    "metrics": [
        (
            "if_in_bps",
            "area",
        ),
        (
            "if_out_bps",
            "-area",
        ),
    ],
    "scalars": [
        ("if_in_bps:warn", _("Warning (In)")),
        ("if_in_bps:crit", _("Critical (In)")),
        ("if_out_bps:warn,-1,*", _("Warning (Out)")),
        ("if_out_bps:crit,-1,*", _("Critical (Out)")),
    ],
}

graph_info["if_errors"] = {
    "title": _("Errors"),
    "metrics": [
        ("if_in_errors", "area"),
        ("if_in_discards", "stack"),
        ("if_out_errors", "-area"),
        ("if_out_discards", "-stack"),
    ],
}

graph_info["bm_packets"] = {
    "title": _("Broad-/Multicast"),
    "metrics": [
        ("if_in_mcast", "line"),
        ("if_in_bcast", "line"),
        ("if_out_mcast", "-line"),
        ("if_out_bcast", "-line"),
    ],
}

graph_info["packets_1"] = {
    "title": _("Packets"),
    "metrics": [
        ("if_in_unicast", "line"),
        ("if_in_non_unicast", "line"),
        ("if_out_unicast", "-line"),
        ("if_out_non_unicast", "-line"),
    ],
}

graph_info["packets_2"] = {
    "title": _("Packets"),
    "metrics": [
        ("if_in_pkts", "area"),
        ("if_out_non_unicast", "-area"),
        ("if_out_unicast", "-stack"),
    ],
}

graph_info["packets_3"] = {
    "title": _("Packets"),
    "metrics": [
        ("if_in_pkts", "area"),
        ("if_out_pkts", "-area"),
    ],
}

graph_info["traffic"] = {
    "title": _("Traffic"),
    "metrics": [
        ("if_in_octets", "area"),
        ("if_out_non_unicast_octets", "-area"),
        ("if_out_unicast_octets", "-stack"),
    ],
}

graph_info["wlan_errors"] = {
    "title": _("WLAN errors, reset operations and transmission retries"),
    "metrics": [
        ("wlan_physical_errors", "area"),
        ("wlan_resets", "stack"),
        ("wlan_retries", "stack"),
    ],
}

graph_info["busy_and_idle_workers"] = {
    "title": _("Busy and idle workers"),
    "metrics": [
        ("busy_workers", "area"),
        ("idle_workers", "stack"),
    ],
}

graph_info["busy_and_idle_servers"] = {
    "title": _("Busy and idle servers"),
    "metrics": [
        ("busy_servers", "area"),
        ("idle_servers", "stack"),
    ],
}

graph_info["total_and_open_slots"] = {
    "title": _("Total and open slots"),
    "metrics": [
        ("total_slots", "area"),
        ("open_slots", "area"),
    ],
}

graph_info["connections"] = {
    "title": _("Connections"),
    "metrics": [
        ("connections", "area"),
        ("connections_async_writing", "area"),
        ("connections_async_keepalive", "stack"),
        ("connections_async_closing", "stack"),
    ],
    "optional_metrics": [
        "connections_async_writing",
        "connections_async_keepalive",
        "connections_async_closing",
    ],
    "scalars": [
        "connections:warn",
        "connections:crit",
    ],
}

graph_info["time_offset"] = {
    "title": _("Time offset"),
    "metrics": [("time_offset", "area"), ("jitter", "line")],
    "scalars": [
        ("time_offset:crit", _("Upper critical level")),
        ("time_offset:warn", _("Upper warning level")),
        ("0,time_offset:warn,-", _("Lower warning level")),
        ("0,time_offset:crit,-", _("Lower critical level")),
    ],
    "range": ("0,time_offset:crit,-", "time_offset:crit"),
    "optional_metrics": ["jitter"],
}

graph_info["firewall_connections"] = {
    "title": _("Firewall connections"),
    "metrics": [
        ("fw_connections_active", "stack"),
        ("fw_connections_established", "stack"),
        ("fw_connections_halfopened", "stack"),
        ("fw_connections_halfclosed", "stack"),
        ("fw_connections_passthrough", "stack"),
    ],
}

graph_info["time_to_connect"] = {
    "title": _("Time to connect"),
    "metrics": [
        ("connection_time", "area"),
    ],
}

graph_info["number_of_total_and_running_sessions"] = {
    "title": _("Number of total and running sessions"),
    "metrics": [
        ("running_sessions", "line"),
        ("total_sessions", "line"),
    ],
}

graph_info["tcp_connection_states"] = {
    "title": _("TCP Connection States"),
    "metrics": [
        ("tcp_listen", "stack"),
        ("tcp_syn_sent", "stack"),
        ("tcp_syn_recv", "stack"),
        ("tcp_established", "stack"),
        ("tcp_time_wait", "stack"),
        ("tcp_last_ack", "stack"),
        ("tcp_close_wait", "stack"),
        ("tcp_closed", "stack"),
        ("tcp_closing", "stack"),
        ("tcp_fin_wait1", "stack"),
        ("tcp_fin_wait2", "stack"),
        ("tcp_bound", "stack"),
        ("tcp_idle", "stack"),
    ],
    "omit_zero_metrics": True,
    "optional_metrics": ["tcp_bound", "tcp_idle"],
}

graph_info["db_connections"] = {
    "title": _("DB Connections"),
    "metrics": [("active_connections", "area"), ("idle_connections", "area")],
    "scalars": [
        ("active_connections:warn", _("Warning (active connections)")),
        ("active_connections:crit", _("Critical (active connections)")),
    ],
}

graph_info["cluster_hosts"] = {
    "title": _("Hosts"),
    "metrics": [
        ("hosts_active", "stack"),
        ("hosts_inactive", "stack"),
        ("hosts_degraded", "stack"),
        ("hosts_offline", "stack"),
        ("hosts_other", "stack"),
    ],
    "optional_metrics": ["hosts_active"],
}

graph_info["modems"] = {
    "title": _("Modems"),
    "metrics": [
        ("active_modems", "area"),
        ("registered_modems", "line"),
        ("total_modems", "line"),
    ],
}

graph_info["net_data_traffic"] = {
    "title": _("Net data traffic"),
    "metrics": [
        ("net_data_recv", "stack"),
        ("net_data_sent", "stack"),
    ],
}

graph_info["access_point_statistics"] = {
    "title": _("Access point statistics"),
    "metrics": [
        ("ap_devices_total", "area"),
        ("ap_devices_drifted", "area"),
        ("ap_devices_not_responding", "stack"),
    ],
}

graph_info["access_point_statistics2"] = {
    "title": _("Access point statistics"),
    "metrics": [("ap_devices_" + ctype, "stack") for ctype in ("cleared", "minor", "critical")],
}

graph_info["wifi_connections"] = {
    "title": _("WiFi connection types"),
    "metrics": [
        ("wifi_connection_dot%s" % ctype, "stack")
        for ctype in ("11a", "11b", "11g", "11ac", "11n2_4", "11n5")
    ],
}

graph_info["round_trip_average"] = {
    "title": _("Round trip average"),
    "metrics": [
        ("rtmax", "area"),
        ("rtmin", "area"),
        ("rta", "line"),
    ],
    "scalars": [
        "rta:warn",
        "rta:crit",
    ],
}

graph_info["packet_loss"] = {
    "title": _("Packet loss"),
    "metrics": [
        ("pl", "area"),
    ],
    "scalars": [
        "pl:warn",
        "pl:crit",
    ],
}


def register_hop_graphs():
    for idx in range(1, MAX_NUMBER_HOPS):
        graph_info["hop_%d_round_trip_average" % idx] = {
            "title": _("Hop %d Round trip average") % idx,
            "metrics": [
                ("hop_%d_rtmax" % idx, "area"),
                ("hop_%d_rtmin" % idx, "area"),
                ("hop_%d_rta" % idx, "line"),
                ("hop_%d_rtstddev" % idx, "line"),
            ],
        }
        graph_info["hop_%d_packet_loss" % idx] = {
            "title": _("Hop %d Packet loss") % idx,
            "metrics": [
                ("hop_%d_pl" % idx, "area"),
            ],
        }


register_hop_graphs()


def register_hop_response_graph() -> None:
    graph_info["hop_response_time"] = {
        "title": _("Hop response times"),
        "metrics": [
            (
                "hop_%d_response_time%s"
                % (idx, parse_color_into_hexrgb(indexed_color(idx, MAX_NUMBER_HOPS))),
                "line",
            )
            for idx in range(1, MAX_NUMBER_HOPS)
        ],
        "optional_metrics": [
            "hop_%d_response_time" % (idx + 1) for idx in range(1, MAX_NUMBER_HOPS) if idx > 0
        ],
    }


register_hop_response_graph()

graph_info["palo_alto_sessions"] = {
    "title": _("Palo Alto Sessions"),
    "metrics": [
        ("tcp_active_sessions", "area"),
        ("udp_active_sessions", "stack"),
        ("icmp_active_sessions", "stack"),
        ("sslproxy_active_sessions", "stack"),
    ],
}

graph_info["page_activity"] = {
    "title": _("Page Activity"),
    "metrics": [
        ("page_reads_sec", "area"),
        ("page_writes_sec", "-area"),
    ],
}

graph_info["authentication_failures"] = {
    "title": _("Authentication Failures"),
    "metrics": [("udp_failed_auth", "line"), ("tcp_failed_auth", "line")],
}

graph_info["allocate_requests_exceeding_port_limit"] = {
    "title": _("Allocate Requests Exceeding Port Limit"),
    "metrics": [
        ("udp_allocate_requests_exceeding_port_limit", "line"),
        ("tcp_allocate_requests_exceeding_port_limit", "line"),
    ],
}

graph_info["packets_dropped"] = {
    "title": _("Packets Dropped"),
    "metrics": [
        ("udp_packets_dropped", "line"),
        ("tcp_packets_dropped", "line"),
    ],
}

graph_info["streams"] = {
    "title": _("Streams"),
    "metrics": [("failed_inbound_streams", "area"), ("failed_outbound_streams", "-area")],
}

graph_info["dhcp_statistics_received"] = {
    "title": _("DHCP statistics (received messages)"),
    "metrics": [
        ("dhcp_discovery", "area"),
        ("dhcp_requests", "stack"),
        ("dhcp_releases", "stack"),
        ("dhcp_declines", "stack"),
        ("dhcp_informs", "stack"),
        ("dhcp_others", "stack"),
    ],
}

graph_info["dhcp_statistics_sent"] = {
    "title": _("DHCP statistics (sent messages)"),
    "metrics": [
        ("dhcp_offers", "area"),
        ("dhcp_acks", "stack"),
        ("dhcp_nacks", "stack"),
    ],
}

graph_info["dns_statistics"] = {
    "title": _("DNS statistics"),
    "metrics": [
        ("dns_successes", "area"),
        ("dns_referrals", "stack"),
        ("dns_recursion", "stack"),
        ("dns_failures", "stack"),
        ("dns_nxrrset", "stack"),
        ("dns_nxdomain", "stack"),
    ],
}

graph_info["connection_durations"] = {
    "title": _("Connection durations"),
    "metrics": [
        ("connections_duration_min", "line"),
        ("connections_duration_max", "line"),
        ("connections_duration_mean", "line"),
    ],
}

graph_info["http_timings"] = {
    "title": _("HTTP Timings"),
    "metrics": [
        ("time_connect", "area", _("Connect")),
        ("time_ssl", "stack", _("Negotiate SSL")),
        ("time_headers", "stack", _("Send request")),
        ("time_transfer", "stack", _("Receive full response")),
        ("time_firstbyte", "line", _("Receive start of response")),
        ("response_time", "line", _("Roundtrip")),
    ],
    "optional_metrics": ["time_ssl"],
}

graph_info["web_gateway_statistics"] = {
    "title": _("Web gateway statistics"),
    "metrics": [
        ("infections_rate", "stack"),
        ("connections_blocked_rate", "stack"),
    ],
}

graph_info["web_gateway_miscellaneous_statistics"] = {
    "title": _("Web gateway miscellaneous statistics"),
    "metrics": [
        ("open_network_sockets", "stack"),
        ("connections", "stack"),
    ],
}

graph_info["DB_connections"] = {
    "title": _("Parallel connections"),
    "metrics": [
        ("connections_max_used", "area"),
        ("connections_conn_threads", "area"),
        ("connections_max", "line"),
    ],
}

graph_info["http_errors"] = {
    "title": _("HTTP Errors"),
    "metrics": [
        ("http_5xx_rate", "area"),
        ("http_4xx_rate", "area"),
    ],
}

graph_info["inodes_used"] = {
    "title": _("Used inodes"),
    "metrics": [
        ("inodes_used", "area"),
    ],
    "scalars": [
        "inodes_used:warn",
        "inodes_used:crit",
        ("inodes_used:max", _("Maximum inodes")),
    ],
    "range": (0, "inodes_used:max"),
}

graph_info["nodes_by_type"] = {
    "title": _("Running nodes by nodes type"),
    "metrics": [
        ("number_of_nodes", "area"),
        ("number_of_data_nodes", "area"),
    ],
}
graph_info["channel_utilization_24ghz"] = {
    "title": _("Channel utilization for 2,4GHz Band"),
    "metrics": [
        ("channel_utilization_24ghz", "area"),
    ],
    "scalars": [
        "channel_utilization_24ghz:warn",
        "channel_utilization_24ghz:crit",
    ],
    "range": (0, 100),
}

graph_info["channel_utilization_5ghz"] = {
    "title": _("Channel utilization for 5GHz Band"),
    "metrics": [
        ("channel_utilization_5ghz", "area"),
    ],
    "scalars": [
        "channel_utilization_5ghz:warn",
        "channel_utilization_5ghz:crit",
    ],
    "range": (0, 100),
}

graph_info["active_sessions_with_peak_value"] = {
    "title": _("Active sessions"),
    "metrics": [
        ("active_sessions", "area"),
        ("active_sessions_peak", "line"),
    ],
    "range": (0, "active_sessions_peak:max"),
    "scalars": [
        "active_sessions:warn",
        "active_sessions:crit",
    ],
}
