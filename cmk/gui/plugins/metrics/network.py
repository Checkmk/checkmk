#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing._utils import graph_info, metric_info
from cmk.gui.i18n import _

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

metric_info["rtt"] = {
    "title": _("Round trip time"),
    "unit": "s",
    "color": "33/a",
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

metric_info["latencies_50"] = {
    "title": _("Latencies (50th percentile)"),
    "unit": "s",
    "color": "21/a",
}
metric_info["latencies_95"] = {
    "title": _("Latencies (95th percentile)"),
    "unit": "s",
    "color": "23/a",
}
metric_info["latencies_99"] = {
    "title": _("Latencies (99th percentile)"),
    "unit": "s",
    "color": "25/a",
}

metric_info["availability"] = {
    "title": _("Availability"),
    "unit": "%",
    "color": "31/a",
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

metric_info["last_sync_time"] = {
    "title": _("Time since last sync"),
    "unit": "s",
    "color": "41/b",
}

metric_info["last_sync_receive_time"] = {
    "title": _("Time since last NTPMessage"),
    "unit": "s",
    "color": "45/b",
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

metric_info["session_rate"] = {
    "title": _("Session rate"),
    "unit": "1/s",
    "color": "#4080a0",
}

metric_info["sync_latency"] = {
    "title": _("Sync latency"),
    "unit": "s",
    "color": "#ffb080",
}

metric_info["wlan_physical_errors"] = {
    "title": "WLAN physical errors",
    "unit": "1/s",
    "color": "14/a",
}

metric_info["wlan_resets"] = {
    "title": "WLAN reset operations",
    "unit": "1/s",
    "color": "21/a",
}

metric_info["wlan_retries"] = {
    "title": "WLAN transmission retries",
    "unit": "1/s",
    "color": "24/a",
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

metric_info["free_dhcp_leases"] = {
    "title": _("Free DHCP leases"),
    "unit": "count",
    "color": "34/a",
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
    "color": "12/a",
}

metric_info["active_modems"] = {
    "title": _("Active modems"),
    "unit": "count",
    "color": "14/a",
}

metric_info["registered_modems"] = {
    "title": _("Registered modems"),
    "unit": "count",
    "color": "16/a",
}

metric_info["channel_utilization_24ghz"] = {
    "title": _("Channel utilization for 2,4GHz band"),
    "unit": "%",
    "color": "25/a",
}

metric_info["channel_utilization_5ghz"] = {
    "title": _("Channel utilization for 5GHz band"),
    "unit": "%",
    "color": "26/a",
}

metric_info["connector_outlets"] = {
    "title": _("Connector outlets"),
    "unit": "count",
    "color": "51/a",
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
    "color": "35/a",
}

metric_info["active_vpn_tunnels"] = {
    "title": _("Active VPN tunnels"),
    "unit": "count",
    "color": "43/a",
}

metric_info["page_reads_sec"] = {
    "title": _("Page reads"),
    "unit": "1/s",
    "color": "33/b",
}

metric_info["page_writes_sec"] = {
    "title": _("Page writes"),
    "unit": "1/s",
    "color": "14/a",
}

metric_info["edge_udp_failed_auth"] = {
    "title": _("UDP authentication failures"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["edge_tcp_failed_auth"] = {
    "title": _("A/V Edge - TCP authentication failures"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["edge_udp_allocate_requests_exceeding_port_limit"] = {
    "title": _("A/V Edge - UDP allocate requests exceeding port limit"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["edge_tcp_allocate_requests_exceeding_port_limit"] = {
    "title": _("A/V Edge - TCP allocate requests exceeding port limit"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["edge_udp_packets_dropped"] = {
    "title": _("A/V Edge - UDP packets dropped"),
    "unit": "1/s",
    "color": "42/a",
}

metric_info["edge_tcp_packets_dropped"] = {
    "title": _("A/V Edge - TCP packets dropped"),
    "unit": "1/s",
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
    "color": "31/a",
}

metric_info["connections_perc_conn_threads"] = {
    "title": _("Open connections load"),
    "unit": "%",
    "color": "31/a",
}

metric_info["connections_perc_used"] = {
    "title": _("Parallel connections load"),
    "unit": "%",
    "color": "42/a",
}

metric_info["current_connections"] = {
    "title": _("Current connections"),
    "unit": "count",
    "color": "24/a",
}

metric_info["new_connections"] = {
    "title": _("New connections"),
    "unit": "count",
    "color": "42/a",
}


metric_info["bytes_downloaded"] = {
    "title": _("Bytes downloaded"),
    "unit": "bytes",
    "color": "42/a",
}

metric_info["bytes_uploaded"] = {
    "title": _("Bytes uploaded"),
    "unit": "bytes",
    "color": "41/b",
}

metric_info["queries_per_sec"] = {
    "title": _("Queries per second"),
    "unit": "1/s",
    "color": "41/b",
}

metric_info["snat_usage"] = {
    "title": _("SNAT usage"),
    "unit": "%",
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
    "title": _("Broadcast/Multicast"),
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

graph_info["last_sync_time"] = {
    "title": _("Time since last synchronisation"),
    "metrics": [("last_sync_time", "line"), ("last_sync_receive_time", "line")],
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
        ("ap_devices_drifted", "line"),
        ("ap_devices_not_responding", "line"),
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
        ("rtmax", "line"),
        ("rtmin", "line"),
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

graph_info["page_activity"] = {
    "title": _("Page activity"),
    "metrics": [
        ("page_reads_sec", "area"),
        ("page_writes_sec", "-area"),
    ],
}

graph_info["authentication_failures"] = {
    "title": _("Authentication failures"),
    "metrics": [
        ("edge_udp_failed_auth", "line"),
        ("edge_tcp_failed_auth", "line"),
    ],
}

graph_info["allocate_requests_exceeding_port_limit"] = {
    "title": _("Allocate requests exceeding port limit"),
    "metrics": [
        ("edge_udp_allocate_requests_exceeding_port_limit", "line"),
        ("edge_tcp_allocate_requests_exceeding_port_limit", "line"),
    ],
}

graph_info["packets_dropped"] = {
    "title": _("Packets dropped"),
    "metrics": [
        ("edge_udp_packets_dropped", "line"),
        ("edge_tcp_packets_dropped", "line"),
    ],
}

graph_info["streams"] = {
    "title": _("Streams"),
    "metrics": [
        ("xmpp_failed_inbound_streams", "area"),
        ("xmpp_failed_outbound_streams", "-area"),
    ],
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
    "title": _("HTTP timings"),
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

graph_info["DB_connections"] = {
    "title": _("Parallel connections"),
    "metrics": [
        ("connections_max_used", "line"),
        ("connections_conn_threads", "line"),
        ("connections_max", "line"),
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
        ("number_of_data_nodes", "line"),
    ],
}
graph_info["channel_utilization_24ghz"] = {
    "title": _("Channel utilization for 2,4GHz band"),
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
    "title": _("Channel utilization for 5GHz band"),
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

graph_info["data_transfer"] = {
    "title": _("Data transfer"),
    "metrics": [
        ("bytes_downloaded", "stack"),
        ("bytes_uploaded", "stack"),
    ],
}

graph_info["latencies"] = {
    "title": _("Latencies"),
    "metrics": [
        ("latencies_50", "line"),
        ("latencies_95", "line"),
        ("latencies_99", "line"),
    ],
}

graph_info["connection_count"] = {
    "title": _("Connections"),
    "metrics": [
        ("current_connections", "line"),
        ("new_connections", "line"),
    ],
}

graph_info["transactions"] = {
    "title": _("Transactions"),
    "metrics": [
        ("transactions", "line"),
    ],
}

graph_info["server_latency"] = {
    "title": _("Server latency"),
    "metrics": [
        ("server_latency", "line"),
    ],
}

graph_info["e2e_latency"] = {
    "title": _("End-to-end latency"),
    "metrics": [
        ("e2e_latency", "line"),
    ],
}

graph_info["availability"] = {
    "title": _("Availability"),
    "metrics": [
        ("availability", "line"),
    ],
}
