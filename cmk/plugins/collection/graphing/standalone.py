#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_DECIBEL_MILLIWATTS = metrics.Unit(metrics.DecimalNotation("dBm"))
UNIT_BYTES_PER_OPERATION = metrics.Unit(metrics.IECNotation("B/op"))
UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))
UNIT_EURO = metrics.Unit(metrics.DecimalNotation("€"), metrics.StrictPrecision(2))
UNIT_DEGREE_CELSIUS = metrics.Unit(metrics.DecimalNotation("°C"))
UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_AMPERE = metrics.Unit(metrics.DecimalNotation("A"), metrics.AutoPrecision(3))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_ELECTRICAL_APPARENT_POWER = metrics.Unit(
    metrics.DecimalNotation("VA"), metrics.AutoPrecision(3)
)
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_HERTZ = metrics.Unit(metrics.DecimalNotation("Hz"))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())
UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""))
UNIT_REVOLUTIONS_PER_MINUTE = metrics.Unit(metrics.DecimalNotation("rpm"), metrics.AutoPrecision(4))

metric_uncommitted = metrics.Metric(
    name="uncommitted",
    title=Title("Uncommitted"),
    unit=UNIT_BYTES,
    color=metrics.Color.ORANGE,
)
metric_overprovisioned = metrics.Metric(
    name="overprovisioned",
    title=Title("Overprovisioned"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
metric_precompiled = metrics.Metric(
    name="precompiled",
    title=Title("Precompiled"),
    unit=UNIT_BYTES,
    color=metrics.Color.ORANGE,
)
metric_hours_operation = metrics.Metric(
    name="hours_operation",
    title=Title("Hours of operation"),
    unit=UNIT_TIME,
    color=metrics.Color.BROWN,
)
metric_hours_since_service = metrics.Metric(
    name="hours_since_service",
    title=Title("Hours since service"),
    unit=UNIT_TIME,
    color=metrics.Color.BROWN,
)
metric_registered_desktops = metrics.Metric(
    name="registered_desktops",
    title=Title("Registered desktops"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_time_in_GC = metrics.Metric(
    name="time_in_GC",
    title=Title("Time spent in GC"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)
metric_service_costs_eur = metrics.Metric(
    name="service_costs_eur",
    title=Title("Service Costs per Day"),
    unit=UNIT_EURO,
    color=metrics.Color.BLUE,
)
metric_fired_alerts = metrics.Metric(
    name="fired_alerts",
    title=Title("Number of fired alerts"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_index_count = metrics.Metric(
    name="index_count",
    title=Title("Indices"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_items_active = metrics.Metric(
    name="items_active",
    title=Title("Active items"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_items_non_res = metrics.Metric(
    name="items_non_res",
    title=Title("Non-resident items"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_num_collections = metrics.Metric(
    name="num_collections",
    title=Title("Collections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_num_objects = metrics.Metric(
    name="num_objects",
    title=Title("Objects"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_num_extents = metrics.Metric(
    name="num_extents",
    title=Title("Extents"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_num_input = metrics.Metric(
    name="num_input",
    title=Title("Inputs"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_num_output = metrics.Metric(
    name="num_output",
    title=Title("Outputs"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_num_stream_rule = metrics.Metric(
    name="num_stream_rule",
    title=Title("Stream rules"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_num_extractor = metrics.Metric(
    name="num_extractor",
    title=Title("Extractors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_activity_log_updates = metrics.Metric(
    name="activity_log_updates",
    title=Title("Activity log updates"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_bit_map_updates = metrics.Metric(
    name="bit_map_updates",
    title=Title("Bit map updates"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_local_count_requests = metrics.Metric(
    name="local_count_requests",
    title=Title("Local count requests"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_YELLOW,
)
metric_pending_requests = metrics.Metric(
    name="pending_requests",
    title=Title("Pending requests"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_unacknowledged_requests = metrics.Metric(
    name="unacknowledged_requests",
    title=Title("Unacknowledged requests"),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_application_pending_requests = metrics.Metric(
    name="application_pending_requests",
    title=Title("Application pending requests"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_epoch_objects = metrics.Metric(
    name="epoch_objects",
    title=Title("Epoch objects"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_collectors_running = metrics.Metric(
    name="collectors_running",
    title=Title("Running collectors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_collectors_stopped = metrics.Metric(
    name="collectors_stopped",
    title=Title("Stopped collectors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_collectors_failing = metrics.Metric(
    name="collectors_failing",
    title=Title("Failing collectors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_PINK,
)
metric_num_streams = metrics.Metric(
    name="num_streams",
    title=Title("Streams"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_item_memory = metrics.Metric(
    name="item_memory",
    title=Title("Item memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_resident_items_ratio = metrics.Metric(
    name="resident_items_ratio",
    title=Title("Resident items ratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_fetched_items = metrics.Metric(
    name="fetched_items",
    title=Title("Number of fetched items"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_YELLOW,
)
metric_consumers = metrics.Metric(
    name="consumers",
    title=Title("Consumers"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_exchanges = metrics.Metric(
    name="exchanges",
    title=Title("Exchanges"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_queues = metrics.Metric(
    name="queues",
    title=Title("Queues"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_gc_runs = metrics.Metric(
    name="gc_runs",
    title=Title("GC runs"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_gc_runs_rate = metrics.Metric(
    name="gc_runs_rate",
    title=Title("GC runs rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BROWN,
)
metric_runtime_run_queue = metrics.Metric(
    name="runtime_run_queue",
    title=Title("Runtime run queue"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_gc_bytes = metrics.Metric(
    name="gc_bytes",
    title=Title("Bytes reclaimed by GC"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)
metric_gc_bytes_rate = metrics.Metric(
    name="gc_bytes_rate",
    title=Title("Bytes reclaimed by GC rate"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_num_topics = metrics.Metric(
    name="num_topics",
    title=Title("Number of topics live"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_sms_spend = metrics.Metric(
    name="sms_spend",
    title=Title("SMS spending"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_accepted = metrics.Metric(
    name="accepted",
    title=Title("Accepted connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_accepted_per_sec = metrics.Metric(
    name="accepted_per_sec",
    title=Title("Accepted connections per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_handled = metrics.Metric(
    name="handled",
    title=Title("Handled connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_handled_per_sec = metrics.Metric(
    name="handled_per_sec",
    title=Title("Handled connections per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_failed_requests = metrics.Metric(
    name="failed_requests",
    title=Title("Failed requests"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_requests_per_conn = metrics.Metric(
    name="requests_per_conn",
    title=Title("Requests per connection"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_requests_per_sec = metrics.Metric(
    name="requests_per_sec",
    title=Title("Requests per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_active = metrics.Metric(
    name="active",
    title=Title("Active connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_reading = metrics.Metric(
    name="reading",
    title=Title("Reading connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_waiting = metrics.Metric(
    name="waiting",
    title=Title("Waiting connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_writing = metrics.Metric(
    name="writing",
    title=Title("Writing connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_apply_finish_time = metrics.Metric(
    name="apply_finish_time",
    title=Title("Apply finish time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_transport_lag = metrics.Metric(
    name="transport_lag",
    title=Title("Transport lag"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_apply_lag = metrics.Metric(
    name="apply_lag",
    title=Title("Apply lag"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)
metric_hops = metrics.Metric(
    name="hops",
    title=Title("Number of hops"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_GRAY,
)
metric_time_difference = metrics.Metric(
    name="time_difference",
    title=Title("Time difference"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_YELLOW,
)
# TODO: Metric names with preceeding numbers seems not to be capable
# of adding scalars with graph_info (e.g. for horizontal warning levels)
metric_5ghz_clients = metrics.Metric(
    name="5ghz_clients",
    title=Title("Client connects for 5 Ghz band"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_PINK,
)
metric_24ghz_clients = metrics.Metric(
    name="24ghz_clients",
    title=Title("Client connects for 2,4 Ghz band"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_connections_failed_rate = metrics.Metric(
    name="connections_failed_rate",
    title=Title("Failed connections"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_failed_connections = metrics.Metric(
    name="failed_connections",
    title=Title("Failed connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_connections_ssl = metrics.Metric(
    name="connections_ssl",
    title=Title("SSL connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_PINK,
)
metric_connections_ssl_vpn = metrics.Metric(
    name="connections_ssl_vpn",
    title=Title("SSL/VPN connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_PINK,
)
metric_connections_rate = metrics.Metric(
    name="connections_rate",
    title=Title("Connections per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GRAY,
)
metric_packet_velocity_asic = metrics.Metric(
    name="packet_velocity_asic",
    title=Title("Packet velocity asic"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_rejected_sessions = metrics.Metric(
    name="rejected_sessions",
    title=Title("Rejected sessions"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_inactive_sessions = metrics.Metric(
    name="inactive_sessions",
    title=Title("Inactive sessions"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_PINK,
)
metric_relay_log_space = metrics.Metric(
    name="relay_log_space",
    title=Title("Relay log size"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_BROWN,
)
metric_p2s_bandwidth = metrics.Metric(
    name="p2s_bandwidth",
    title=Title("Point-to-site bandwidth"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_s2s_bandwidth = metrics.Metric(
    name="s2s_bandwidth",
    title=Title("Site-to-site bandwidth"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)
# “Output Queue Length is the length of the output packet queue (in
# packets). If this is longer than two, there are delays and the bottleneck
# should be found and eliminated, if possible.
metric_outqlen = metrics.Metric(
    name="outqlen",
    title=Title("Length of output queue"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_average_sync_time = metrics.Metric(
    name="average_sync_time",
    title=Title("Average remote site sync time"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_average_processing_time = metrics.Metric(
    name="average_processing_time",
    title=Title("Event processing time"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_PINK,
)
metric_average_rule_hit_ratio = metrics.Metric(
    name="average_rule_hit_ratio",
    title=Title("Rule hit ratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_GRAY,
)
metric_used_dhcp_leases = metrics.Metric(
    name="used_dhcp_leases",
    title=Title("Used DHCP leases"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GRAY,
)
metric_pending_dhcp_leases = metrics.Metric(
    name="pending_dhcp_leases",
    title=Title("Pending DHCP leases"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_channel_utilization = metrics.Metric(
    name="channel_utilization",
    title=Title("Channel utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_response_size = metrics.Metric(
    name="response_size",
    title=Title("Response size"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_GRAY,
)
# time_http_headers/time_http_body come from check_httpv2 and correspond
# to time_headers/time_transfer from the old check_http.
# We keep the old metrics as long as the old check_http is still in use.
metric_time_http_headers = metrics.Metric(
    name="time_http_headers",
    title=Title("Time to fetch HTTP headers"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_time_http_body = metrics.Metric(
    name="time_http_body",
    title=Title("Time to fetch page content"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_wifi_connection_dot11ax2_4 = metrics.Metric(
    name="wifi_connection_dot11ax2_4",
    title=Title("802.dot11ax2_4"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_wifi_connection_dot11ax5 = metrics.Metric(
    name="wifi_connection_dot11ax5",
    title=Title("802.dot11ax5"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_server_conns = metrics.Metric(
    name="server_conns",
    title=Title("Server connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_client_conns = metrics.Metric(
    name="client_conns",
    title=Title("Client connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_error_rate = metrics.Metric(
    name="error_rate",
    title=Title("Error rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_managed_object_count = metrics.Metric(
    name="managed_object_count",
    title=Title("Managed objects"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_active_vpn_users = metrics.Metric(
    name="active_vpn_users",
    title=Title("Active VPN users"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_active_vpn_websessions = metrics.Metric(
    name="active_vpn_websessions",
    title=Title("Active VPN web sessions"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_total_active_sessions = metrics.Metric(
    name="total_active_sessions",
    title=Title("Total active sessions"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_GRAY,
)
metric_packages_accepted = metrics.Metric(
    name="packages_accepted",
    title=Title("Accepted packages/s"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
metric_packages_blocked = metrics.Metric(
    name="packages_blocked",
    title=Title("Blocked packages/s"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_packages_icmp_total = metrics.Metric(
    name="packages_icmp_total",
    title=Title("ICMP packages/s"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_locks_per_batch = metrics.Metric(
    name="locks_per_batch",
    title=Title("Locks/batch"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)
metric_page_lookups_sec = metrics.Metric(
    name="page_lookups_sec",
    title=Title("Page lookups"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_failed_search_requests = metrics.Metric(
    name="failed_search_requests",
    title=Title("WEB - Failed search requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_failed_location_requests = metrics.Metric(
    name="failed_location_requests",
    title=Title("WEB - Failed get locations requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_failed_ad_requests = metrics.Metric(
    name="failed_ad_requests",
    title=Title("WEB - Timed out Active Directory requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_http_5xx = metrics.Metric(
    name="http_5xx",
    title=Title("HTTP 500 errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_sip_message_processing_time = metrics.Metric(
    name="sip_message_processing_time",
    title=Title("SIP - Average incoming message processing time"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_BLUE,
)
metric_asp_requests_rejected = metrics.Metric(
    name="asp_requests_rejected",
    title=Title("ASP requests rejected"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_failed_file_requests = metrics.Metric(
    name="failed_file_requests",
    title=Title("Failed file requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_join_failures = metrics.Metric(
    name="join_failures",
    title=Title("Join Launcher service failures"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_failed_validate_cert_calls = metrics.Metric(
    name="failed_validate_cert_calls",
    title=Title("WEB - Failed validate cert calls"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_sip_incoming_responses_dropped = metrics.Metric(
    name="sip_incoming_responses_dropped",
    title=Title("SIP - Incoming responses dropped"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_sip_incoming_requests_dropped = metrics.Metric(
    name="sip_incoming_requests_dropped",
    title=Title("SIP - Incoming requests dropped"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_usrv_queue_latency = metrics.Metric(
    name="usrv_queue_latency",
    title=Title("USrv - Queue latency"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_BLUE,
)
metric_usrv_sproc_latency = metrics.Metric(
    name="usrv_sproc_latency",
    title=Title("USrv - Sproc latency"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_BLUE,
)
metric_usrv_throttled_requests = metrics.Metric(
    name="usrv_throttled_requests",
    title=Title("USrv - Throttled requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_sip_503_responses = metrics.Metric(
    name="sip_503_responses",
    title=Title("SIP - Local 503 responses"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_sip_incoming_messages_timed_out = metrics.Metric(
    name="sip_incoming_messages_timed_out",
    title=Title("SIP - Incoming messages timed out"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_caa_incomplete_calls = metrics.Metric(
    name="caa_incomplete_calls",
    title=Title("CAA - Incomplete calls"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_usrv_create_conference_latency = metrics.Metric(
    name="usrv_create_conference_latency",
    title=Title("USrv - Create conference latency"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_BLUE,
)
metric_usrv_allocation_latency = metrics.Metric(
    name="usrv_allocation_latency",
    title=Title("USrv - Allocation latency"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_BLUE,
)
metric_sip_avg_holding_time_incoming_messages = metrics.Metric(
    name="sip_avg_holding_time_incoming_messages",
    title=Title("SIP - Average holding time for incoming messages"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_BLUE,
)
metric_sip_flow_controlled_connections = metrics.Metric(
    name="sip_flow_controlled_connections",
    title=Title("SIP - Flow-controlled connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_sip_avg_outgoing_queue_delay = metrics.Metric(
    name="sip_avg_outgoing_queue_delay",
    title=Title("SIP - Average outgoing queue delay"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_BLUE,
)
metric_sip_sends_timed_out = metrics.Metric(
    name="sip_sends_timed_out",
    title=Title("SIP - Sends timed out"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_sip_authentication_errors = metrics.Metric(
    name="sip_authentication_errors",
    title=Title("SIP - Authentication errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_mediation_load_call_failure_index = metrics.Metric(
    name="mediation_load_call_failure_index",
    title=Title("MediationServer - Load call failure index"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_mediation_failed_calls_because_of_proxy = metrics.Metric(
    name="mediation_failed_calls_because_of_proxy",
    title=Title("MediationServer - Failed calls caused by unexpected interaction from proxy"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_mediation_failed_calls_because_of_gateway = metrics.Metric(
    name="mediation_failed_calls_because_of_gateway",
    title=Title("MediationServer - Failed calls caused by unexpected interaction from gateway"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_mediation_media_connectivity_failure = metrics.Metric(
    name="mediation_media_connectivity_failure",
    title=Title("Mediation Server - Media connectivity check failure"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_avauth_failed_requests = metrics.Metric(
    name="avauth_failed_requests",
    title=Title("A/V Auth - Bad requests received"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_tcp_packets_received = metrics.Metric(
    name="tcp_packets_received",
    title=Title("Received TCP packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_udp_packets_received = metrics.Metric(
    name="udp_packets_received",
    title=Title("Received UDP packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_icmp_packets_received = metrics.Metric(
    name="icmp_packets_received",
    title=Title("Received ICMP packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_dataproxy_connections_throttled = metrics.Metric(
    name="dataproxy_connections_throttled",
    title=Title("DATAPROXY - Throttled server connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_web_requests_processing = metrics.Metric(
    name="web_requests_processing",
    title=Title("WEB - Requests in processing"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_PINK,
)
metric_time_to_resolve_dns = metrics.Metric(
    name="time_to_resolve_dns",
    title=Title("Time to resolve DNS"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_time_consumed_by_rule_engine = metrics.Metric(
    name="time_consumed_by_rule_engine",
    title=Title("Time consumed by rule engine"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_inside_macs = metrics.Metric(
    name="inside_macs",
    title=Title("Number of unique inside MAC addresses"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_outside_macs = metrics.Metric(
    name="outside_macs",
    title=Title("Number of unique outside MAC addresses"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_avg_response_time = metrics.Metric(
    name="avg_response_time",
    title=Title("Average response time"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_BLUE,
)
metric_remaining_reads = metrics.Metric(
    name="remaining_reads",
    title=Title("Remaining reads"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_dtu_percent = metrics.Metric(
    name="dtu_percent",
    title=Title("Database throughput unit"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_rpc_backlog = metrics.Metric(
    name="rpc_backlog",
    title=Title("RPC Backlog"),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_GREEN,
)
metric_read_ops = metrics.Metric(
    name="read_ops",
    title=Title("Read operations"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_read_b_s = metrics.Metric(
    name="read_b_s",
    title=Title("Read size per second"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
metric_read_b_op = metrics.Metric(
    name="read_b_op",
    title=Title("Read size per operation"),
    unit=UNIT_BYTES_PER_OPERATION,
    color=metrics.Color.DARK_CYAN,
)
metric_read_retrans = metrics.Metric(
    name="read_retrans",
    title=Title("Read retransmission"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_GREEN,
)
metric_write_retrans = metrics.Metric(
    name="write_retrans",
    title=Title("Write retransmission"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_GREEN,
)
metric_read_avg_rtt_s = metrics.Metric(
    name="read_avg_rtt_s",
    title=Title("Read average rtt"),
    unit=UNIT_TIME,
    color=metrics.Color.LIGHT_GREEN,
)
metric_read_avg_exe_s = metrics.Metric(
    name="read_avg_exe_s",
    title=Title("Read average exe"),
    unit=UNIT_TIME,
    color=metrics.Color.LIGHT_GREEN,
)
metric_write_ops_s = metrics.Metric(
    name="write_ops_s",
    title=Title("Write operations"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_write_b_s = metrics.Metric(
    name="write_b_s",
    title=Title("Writes size per second"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
metric_write_b_op = metrics.Metric(
    name="write_b_op",
    title=Title("Writes size per operation"),
    unit=UNIT_BYTES_PER_OPERATION,
    color=metrics.Color.DARK_CYAN,
)
metric_write_avg_rtt_s = metrics.Metric(
    name="write_avg_rtt_s",
    title=Title("Write average rtt"),
    unit=UNIT_TIME,
    color=metrics.Color.LIGHT_GREEN,
)
metric_write_avg_exe_s = metrics.Metric(
    name="write_avg_exe_s",
    title=Title("Write average exe"),
    unit=UNIT_TIME,
    color=metrics.Color.LIGHT_GREEN,
)
metric_get_requests = metrics.Metric(
    name="get_requests",
    title=Title("GET requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_get_requests_perc = metrics.Metric(
    name="get_requests_perc",
    title=Title("Percentage GET requests"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_put_requests = metrics.Metric(
    name="put_requests",
    title=Title("PUT requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
metric_put_requests_perc = metrics.Metric(
    name="put_requests_perc",
    title=Title("Percentage PUT requests"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_delete_requests = metrics.Metric(
    name="delete_requests",
    title=Title("DELETE requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_delete_requests_perc = metrics.Metric(
    name="delete_requests_perc",
    title=Title("Percentage DELETE requests"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)
metric_head_requests = metrics.Metric(
    name="head_requests",
    title=Title("HEAD requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_head_requests_perc = metrics.Metric(
    name="head_requests_perc",
    title=Title("Percentage HEAD requests"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_post_requests = metrics.Metric(
    name="post_requests",
    title=Title("POST requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_post_requests_perc = metrics.Metric(
    name="post_requests_perc",
    title=Title("Percentage POST requests"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_select_requests = metrics.Metric(
    name="select_requests",
    title=Title("SELECT requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_select_requests_perc = metrics.Metric(
    name="select_requests_perc",
    title=Title("Percentage SELECT requests"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_list_requests = metrics.Metric(
    name="list_requests",
    title=Title("LIST requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_list_requests_perc = metrics.Metric(
    name="list_requests_perc",
    title=Title("Percentage LIST requests"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_channels = metrics.Metric(
    name="channels",
    title=Title("Channels"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_bytes_accepted = metrics.Metric(
    name="bytes_accepted",
    title=Title("Bytes accepted"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_bytes_dropped = metrics.Metric(
    name="bytes_dropped",
    title=Title("Bytes dropped"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_bytes_rejected = metrics.Metric(
    name="bytes_rejected",
    title=Title("Bytes rejected"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_packets = metrics.Metric(
    name="packets",
    title=Title("Total number of packets"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_packets_accepted = metrics.Metric(
    name="packets_accepted",
    title=Title("Packets accepted"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_packets_dropped = metrics.Metric(
    name="packets_dropped",
    title=Title("Packets dropped"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_packets_rejected = metrics.Metric(
    name="packets_rejected",
    title=Title("Packets rejected"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_fortiauthenticator_fails_5min = metrics.Metric(
    name="fortiauthenticator_fails_5min",
    title=Title("Authentication failures (last 5 minutes)"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_fortigate_detection_rate = metrics.Metric(
    name="fortigate_detection_rate",
    title=Title("Detection rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_fortigate_blocking_rate = metrics.Metric(
    name="fortigate_blocking_rate",
    title=Title("Blocking rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_ap_count = metrics.Metric(
    name="ap_count",
    title=Title("Number of access points"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_clients_count = metrics.Metric(
    name="clients_count",
    title=Title("Number of clients"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_byte_count = metrics.Metric(
    name="byte_count",
    title=Title("Byte count"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_allocated_snat_ports = metrics.Metric(
    name="allocated_snat_ports",
    title=Title("Allocated SNAT ports"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_used_snat_ports = metrics.Metric(
    name="used_snat_ports",
    title=Title("Used SNAT ports"),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_BLUE,
)
metric_power_usage_percentage = metrics.Metric(
    name="power_usage_percentage",
    title=Title("Power Usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_signal_power_dbm = metrics.Metric(
    name="signal_power_dbm",
    title=Title("Power"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.DARK_CYAN,
)
metric_differential_current_ac = metrics.Metric(
    name="differential_current_ac",
    title=Title("Differential current AC"),
    unit=UNIT_AMPERE,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_differential_current_dc = metrics.Metric(
    name="differential_current_dc",
    title=Title("Differential current DC"),
    unit=UNIT_AMPERE,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_appower = metrics.Metric(
    name="appower",
    title=Title("Electrical apparent power"),
    unit=UNIT_ELECTRICAL_APPARENT_POWER,
    color=metrics.Color.DARK_YELLOW,
)
metric_noise_floor = metrics.Metric(
    name="noise_floor",
    title=Title("Noise floor"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.PURPLE,
)
metric_frequency = metrics.Metric(
    name="frequency",
    title=Title("Frequency"),
    unit=UNIT_HERTZ,
    color=metrics.Color.PURPLE,
)
metric_battery_temp = metrics.Metric(
    name="battery_temp",
    title=Title("Battery temperature"),
    unit=UNIT_DEGREE_CELSIUS,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_o2_percentage = metrics.Metric(
    name="o2_percentage",
    title=Title("Current O2 percentage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_port_temp_0 = metrics.Metric(
    name="port_temp_0",
    title=Title("Temperature Lane 1"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.CYAN,
)
metric_port_temp_1 = metrics.Metric(
    name="port_temp_1",
    title=Title("Temperature Lane 2"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.DARK_YELLOW,
)
metric_port_temp_2 = metrics.Metric(
    name="port_temp_2",
    title=Title("Temperature Lane 3"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.DARK_PINK,
)
metric_port_temp_3 = metrics.Metric(
    name="port_temp_3",
    title=Title("Temperature Lane 4"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.DARK_BLUE,
)
metric_port_temp_4 = metrics.Metric(
    name="port_temp_4",
    title=Title("Temperature Lane 5"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.BLUE,
)
metric_port_temp_5 = metrics.Metric(
    name="port_temp_5",
    title=Title("Temperature Lane 6"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.YELLOW,
)
metric_port_temp_6 = metrics.Metric(
    name="port_temp_6",
    title=Title("Temperature Lane 7"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_port_temp_7 = metrics.Metric(
    name="port_temp_7",
    title=Title("Temperature Lane 8"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.PURPLE,
)
metric_port_temp_8 = metrics.Metric(
    name="port_temp_8",
    title=Title("Temperature Lane 9"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.CYAN,
)
metric_port_temp_9 = metrics.Metric(
    name="port_temp_9",
    title=Title("Temperature Lane 10"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.DARK_YELLOW,
)
metric_deferred_age = metrics.Metric(
    name="deferred_age",
    title=Title("Deferred files age"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_YELLOW,
)
metric_lifetime_remaining = metrics.Metric(
    name="lifetime_remaining",
    title=Title("Lifetime remaining"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_YELLOW,
)
metric_cache_misses_rate = metrics.Metric(
    name="cache_misses_rate",
    title=Title("Cache misses per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_zfs_l2_size = metrics.Metric(
    name="zfs_l2_size",
    title=Title("L2 cache size"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)
metric_ingress_packet_drop = metrics.Metric(
    name="ingress_packet_drop",
    title=Title("Ingress packet drop"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_egress_packet_drop = metrics.Metric(
    name="egress_packet_drop",
    title=Title("Egress packet drop"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_data_files = metrics.Metric(
    name="data_files",
    title=Title("Data files size"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)
metric_log_files_used = metrics.Metric(
    name="log_files_used",
    title=Title("Used size of log files"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
metric_log_files_total = metrics.Metric(
    name="log_files_total",
    title=Title("Total size of log files"),
    unit=UNIT_BYTES,
    color=metrics.Color.ORANGE,
)
metric_size_on_disk = metrics.Metric(
    name="size_on_disk",
    title=Title("Size on disk"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_YELLOW,
)
metric_mem_available = metrics.Metric(
    name="mem_available",
    title=Title("Estimated RAM for new processes"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
metric_trend_hoursleft = metrics.Metric(
    name="trend_hoursleft",
    title=Title("Time left until full"),
    unit=UNIT_TIME,
    color=metrics.Color.BROWN,
)
metric_swap_free = metrics.Metric(
    name="swap_free",
    title=Title("Free swap space"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_BLUE,
)
metric_swap_used_percent = metrics.Metric(
    name="swap_used_percent",
    title=Title("Swap used"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_caches = metrics.Metric(
    name="caches",
    title=Title("Memory used by caches"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_GRAY,
)
metric_mem_lnx_total_used = metrics.Metric(
    name="mem_lnx_total_used",
    title=Title("Total used memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_mem_lnx_pending = metrics.Metric(
    name="mem_lnx_pending",
    title=Title("Pending memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
metric_mem_lnx_unevictable = metrics.Metric(
    name="mem_lnx_unevictable",
    title=Title("Unevictable memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_mem_lnx_anon_pages = metrics.Metric(
    name="mem_lnx_anon_pages",
    title=Title("Anonymous pages"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_ORANGE,
)
metric_mem_lnx_shmem = metrics.Metric(
    name="mem_lnx_shmem",
    title=Title("Shared memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_YELLOW,
)
metric_mem_lnx_mapped = metrics.Metric(
    name="mem_lnx_mapped",
    title=Title("Mapped data"),
    unit=UNIT_BYTES,
    color=metrics.Color.GRAY,
)
metric_mem_lnx_anon_huge_pages = metrics.Metric(
    name="mem_lnx_anon_huge_pages",
    title=Title("Anonymous huge pages"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_BLUE,
)
metric_mem_lnx_hardware_corrupted = metrics.Metric(
    name="mem_lnx_hardware_corrupted",
    title=Title("Hardware corrupted memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_PINK,
)
metric_pagefile_total = metrics.Metric(
    name="pagefile_total",
    title=Title("Pagefile installed"),
    unit=UNIT_BYTES,
    color=metrics.Color.LIGHT_GRAY,
)
metric_mem_fragmentation = metrics.Metric(
    name="mem_fragmentation",
    title=Title("Memory fragmentation"),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_evictions = metrics.Metric(
    name="evictions",
    title=Title("Evictions"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_CYAN,
)
metric_reclaimed = metrics.Metric(
    name="reclaimed",
    title=Title("Reclaimed"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_disk_min_read_wait = metrics.Metric(
    name="disk_min_read_wait",
    title=Title("Minimum read wait time"),
    unit=UNIT_TIME,
    color=metrics.Color.CYAN,
)
metric_disk_max_read_wait = metrics.Metric(
    name="disk_max_read_wait",
    title=Title("Maximum read wait time"),
    unit=UNIT_TIME,
    color=metrics.Color.CYAN,
)
metric_disk_min_write_wait = metrics.Metric(
    name="disk_min_write_wait",
    title=Title("Minimum write wait time"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_disk_max_write_wait = metrics.Metric(
    name="disk_max_write_wait",
    title=Title("Maximum write wait time"),
    unit=UNIT_TIME,
    color=metrics.Color.CYAN,
)
metric_other_latency = metrics.Metric(
    name="other_latency",
    title=Title("Other latency"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)
metric_disk_used_capacity = metrics.Metric(
    name="disk_used_capacity",
    title=Title("Used disk capacity"),
    unit=UNIT_BYTES,
    color=metrics.Color.ORANGE,
)
metric_files_open = metrics.Metric(
    name="files_open",
    title=Title("Open files"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_directories = metrics.Metric(
    name="directories",
    title=Title("Directories"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_backup_avgspeed = metrics.Metric(
    name="backup_avgspeed",
    title=Title("Average speed of backup"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_backup_duration = metrics.Metric(
    name="backup_duration",
    title=Title("Duration of backup"),
    unit=UNIT_TIME,
    color=metrics.Color.CYAN,
)
metric_readsize = metrics.Metric(
    name="readsize",
    title=Title("Readsize"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_PINK,
)
metric_transferredsize = metrics.Metric(
    name="transferredsize",
    title=Title("Transferredsize"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_PINK,
)
metric_backup_age_database = metrics.Metric(
    name="backup_age_database",
    title=Title("Age of last database backup"),
    unit=UNIT_TIME,
    color=metrics.Color.PURPLE,
)
metric_backup_age_database_diff = metrics.Metric(
    name="backup_age_database_diff",
    title=Title("Age of last differential database backup"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_backup_age_log = metrics.Metric(
    name="backup_age_log",
    title=Title("Age of last log backup"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)
metric_backup_age_file_or_filegroup = metrics.Metric(
    name="backup_age_file_or_filegroup",
    title=Title("Age of last file or filegroup backup"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)
metric_backup_age_file_diff = metrics.Metric(
    name="backup_age_file_diff",
    title=Title("Age of last differential file backup"),
    unit=UNIT_TIME,
    color=metrics.Color.CYAN,
)
metric_backup_age_partial = metrics.Metric(
    name="backup_age_partial",
    title=Title("Age of last partial backup"),
    unit=UNIT_TIME,
    color=metrics.Color.CYAN,
)
metric_backup_age_differential_partial = metrics.Metric(
    name="backup_age_differential_partial",
    title=Title("Age of last differential partial backup"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_nfs_ios = metrics.Metric(
    name="nfs_ios",
    title=Title("NFS operations"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_nfsv4_ios = metrics.Metric(
    name="nfsv4_ios",
    title=Title("NFSv4 operations"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_nfsv4_1_ios = metrics.Metric(
    name="nfsv4_1_ios",
    title=Title("NFSv4.1 operations"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_harddrive_uncorrectable_erros = metrics.Metric(
    name="harddrive_uncorrectable_erros",
    title=Title("Harddrive uncorrectable errors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_harddrive_crc_errors = metrics.Metric(
    name="harddrive_crc_errors",
    title=Title("Harddrive CRC errors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_nvme_media_and_data_integrity_errors = metrics.Metric(
    name="nvme_media_and_data_integrity_errors",
    title=Title("Media and data integrity errors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_nvme_error_information_log_entries = metrics.Metric(
    name="nvme_error_information_log_entries",
    title=Title("Error information log entries"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_nvme_critical_warning = metrics.Metric(
    name="nvme_critical_warning",
    title=Title("Critical warning"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_nvme_available_spare = metrics.Metric(
    name="nvme_available_spare",
    title=Title("Available spare"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_nvme_spare_percentage_used = metrics.Metric(
    name="nvme_spare_percentage_used",
    title=Title("Percentage used"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_nvme_data_units_read = metrics.Metric(
    name="nvme_data_units_read",
    title=Title("Data units read"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)
metric_nvme_data_units_written = metrics.Metric(
    name="nvme_data_units_written",
    title=Title("Data units written"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
metric_data_usage = metrics.Metric(
    name="data_usage",
    title=Title("Data usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_meta_usage = metrics.Metric(
    name="meta_usage",
    title=Title("Meta usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.CYAN,
)
metric_storage_used = metrics.Metric(
    name="storage_used",
    title=Title("Storage space used"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_storage_percent = metrics.Metric(
    name="storage_percent",
    title=Title("Storage space used"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_available_file_descriptors = metrics.Metric(
    name="available_file_descriptors",
    title=Title("Number of available file descriptors"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_mem_total_virtual_in_bytes = metrics.Metric(
    name="mem_total_virtual_in_bytes",
    title=Title("Total virtual memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_BROWN,
)
metric_store_size = metrics.Metric(
    name="store_size",
    title=Title("Store size"),
    unit=UNIT_BYTES,
    color=metrics.Color.CYAN,
)
metric_id_cache_size = metrics.Metric(
    name="id_cache_size",
    title=Title("ID cache size"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
metric_field_data_size = metrics.Metric(
    name="field_data_size",
    title=Title("Field data size"),
    unit=UNIT_BYTES,
    color=metrics.Color.ORANGE,
)
metric_avg_doc_size = metrics.Metric(
    name="avg_doc_size",
    title=Title("Average document size"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_YELLOW,
)
metric_disk_fill_rate = metrics.Metric(
    name="disk_fill_rate",
    title=Title("Disk fill rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_disk_drain_rate = metrics.Metric(
    name="disk_drain_rate",
    title=Title("Disk drain rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)
metric_memory_used = metrics.Metric(
    name="memory_used",
    title=Title("Memory used"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
# In order to use the "bytes" unit we would have to change the output of the check, (i.e. divide by
# 1024) which means an invalidation of historic values.
metric_kb_out_of_sync = metrics.Metric(
    name="kb_out_of_sync",
    title=Title("Out of sync"),
    unit=UNIT_BYTES,
    color=metrics.Color.ORANGE,
)
metric_serverlog_storage_percent = metrics.Metric(
    name="serverlog_storage_percent",
    title=Title("Server log storage used"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_hosts_healthy = metrics.Metric(
    name="hosts_healthy",
    title=Title("Healthy hosts"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_num_high_alerts = metrics.Metric(
    name="num_high_alerts",
    title=Title("High alerts"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_num_disabled_alerts = metrics.Metric(
    name="num_disabled_alerts",
    title=Title("Disabled alerts"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_age_oldest = metrics.Metric(
    name="age_oldest",
    title=Title("Oldest age"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_age_youngest = metrics.Metric(
    name="age_youngest",
    title=Title("Youngest age"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)
metric_fs_provisioning = metrics.Metric(
    name="fs_provisioning",
    title=Title("Provisioned space"),
    unit=UNIT_BYTES,
    color=metrics.Color.ORANGE,
)
metric_data_reduction = metrics.Metric(
    name="data_reduction",
    title=Title("Data reduction ratio"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_predict_load15 = metrics.Metric(
    name="predict_load15",
    title=Title("Predicted average for 15 minute CPU load"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GRAY,
)
metric_load_instant = metrics.Metric(
    name="load_instant",
    title=Title("Instantaneous CPU load"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BLUE,
)
metric_threads_rate = metrics.Metric(
    name="threads_rate",
    title=Title("Thread creations per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_threads_total = metrics.Metric(
    name="threads_total",
    title=Title("Number of threads"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_util1s = metrics.Metric(
    name="util1s",
    title=Title("CPU utilization last second"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GREEN,
)
metric_util5s = metrics.Metric(
    name="util5s",
    title=Title("CPU utilization last five seconds"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BROWN,
)
metric_util5 = metrics.Metric(
    name="util5",
    title=Title("CPU utilization last 5 minutes"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_GREEN,
)
metric_cpu_time_percent = metrics.Metric(
    name="cpu_time_percent",
    title=Title("CPU time"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_app = metrics.Metric(
    name="app",
    title=Title("Available physical processors in shared pool"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_entc = metrics.Metric(
    name="entc",
    title=Title("Entitled capacity consumed"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_lbusy = metrics.Metric(
    name="lbusy",
    title=Title("Logical processor(s) utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_nsp = metrics.Metric(
    name="nsp",
    title=Title("Average processor speed"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)
metric_phint = metrics.Metric(
    name="phint",
    title=Title("Phantom interruptions received"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_physc = metrics.Metric(
    name="physc",
    title=Title("Physical processors consumed"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_utcyc = metrics.Metric(
    name="utcyc",
    title=Title("Unaccounted turbo cycles"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_vcsw = metrics.Metric(
    name="vcsw",
    title=Title("Virtual context switches"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_job_total = metrics.Metric(
    name="job_total",
    title=Title("Total number of jobs"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_failed_jobs = metrics.Metric(
    name="failed_jobs",
    title=Title("Total number of failed jobs"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_zombie_jobs = metrics.Metric(
    name="zombie_jobs",
    title=Title("Total number of zombie jobs"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_cpu_percent = metrics.Metric(
    name="cpu_percent",
    title=Title("CPU used"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)
metric_cpu_total_in_millis = metrics.Metric(
    name="cpu_total_in_millis",
    title=Title("CPU total in ms"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_nfs_other_data = metrics.Metric(
    name="nfs_other_data",
    title=Title("NFS other data"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
metric_nfs_other_latency = metrics.Metric(
    name="nfs_other_latency",
    title=Title("NFS other latency"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)
metric_nfs_read_ios = metrics.Metric(
    name="nfs_read_ios",
    title=Title("NFS read ios"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_nfs_write_ios = metrics.Metric(
    name="nfs_write_ios",
    title=Title("NFS write ios"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_nfs_read_throughput = metrics.Metric(
    name="nfs_read_throughput",
    title=Title("NFS read throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_nfs_write_throughput = metrics.Metric(
    name="nfs_write_throughput",
    title=Title("NFS write throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_nfs_other_ops = metrics.Metric(
    name="nfs_other_ops",
    title=Title("NFS other ops"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_nfsv4_other_data = metrics.Metric(
    name="nfsv4_other_data",
    title=Title("NFSv4 other data"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
metric_nfsv4_other_latency = metrics.Metric(
    name="nfsv4_other_latency",
    title=Title("NFSv4 other latency"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)
metric_nfsv4_read_ios = metrics.Metric(
    name="nfsv4_read_ios",
    title=Title("NFSv4 read ios"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_nfsv4_write_ios = metrics.Metric(
    name="nfsv4_write_ios",
    title=Title("NFSv4 write ios"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_nfsv4_read_throughput = metrics.Metric(
    name="nfsv4_read_throughput",
    title=Title("NFSv4 read throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_nfsv4_write_throughput = metrics.Metric(
    name="nfsv4_write_throughput",
    title=Title("NFSv4 write throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_nfsv4_other_ops = metrics.Metric(
    name="nfsv4_other_ops",
    title=Title("NFSv4 other ops"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_nfsv4_1_other_data = metrics.Metric(
    name="nfsv4_1_other_data",
    title=Title("NFSv4.1 other data"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
metric_nfsv4_1_other_latency = metrics.Metric(
    name="nfsv4_1_other_latency",
    title=Title("NFSv4.1 other latency"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)
metric_nfsv4_1_read_ios = metrics.Metric(
    name="nfsv4_1_read_ios",
    title=Title("NFSv4.1 read ios"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_nfsv4_1_write_ios = metrics.Metric(
    name="nfsv4_1_write_ios",
    title=Title("NFSv4.1 write ios"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_nfsv4_1_read_throughput = metrics.Metric(
    name="nfsv4_1_read_throughput",
    title=Title("NFSv4.1 read throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_nfsv4_1_write_throughput = metrics.Metric(
    name="nfsv4_1_write_throughput",
    title=Title("NFSv4.1 write throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_nfsv4_1_other_ops = metrics.Metric(
    name="nfsv4_1_other_ops",
    title=Title("NFSv4.1 other ops"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_cifs_other_data = metrics.Metric(
    name="cifs_other_data",
    title=Title("CIFS other data"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
metric_cifs_other_latency = metrics.Metric(
    name="cifs_other_latency",
    title=Title("CIFS other latency"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)
metric_cifs_read_ios = metrics.Metric(
    name="cifs_read_ios",
    title=Title("CIFS read ios"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_cifs_write_ios = metrics.Metric(
    name="cifs_write_ios",
    title=Title("CIFS write ios"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_cifs_read_throughput = metrics.Metric(
    name="cifs_read_throughput",
    title=Title("CIFS read throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_cifs_write_throughput = metrics.Metric(
    name="cifs_write_throughput",
    title=Title("CIFS write throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_cifs_other_ops = metrics.Metric(
    name="cifs_other_ops",
    title=Title("CIFS other ops"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_san_other_data = metrics.Metric(
    name="san_other_data",
    title=Title("SAN other data"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
metric_san_other_latency = metrics.Metric(
    name="san_other_latency",
    title=Title("SAN other latency"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)
metric_san_read_ios = metrics.Metric(
    name="san_read_ios",
    title=Title("SAN read ios"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_san_write_ios = metrics.Metric(
    name="san_write_ios",
    title=Title("SAN write ios"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_san_read_throughput = metrics.Metric(
    name="san_read_throughput",
    title=Title("SAN read throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_san_write_throughput = metrics.Metric(
    name="san_write_throughput",
    title=Title("SAN write throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_san_other_ops = metrics.Metric(
    name="san_other_ops",
    title=Title("SAN other ops"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_fcp_other_data = metrics.Metric(
    name="fcp_other_data",
    title=Title("FCP other data"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
metric_fcp_other_latency = metrics.Metric(
    name="fcp_other_latency",
    title=Title("FCP other latency"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)
metric_fcp_read_ios = metrics.Metric(
    name="fcp_read_ios",
    title=Title("FCP read ios"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_fcp_write_ios = metrics.Metric(
    name="fcp_write_ios",
    title=Title("FCP write ios"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_fcp_read_throughput = metrics.Metric(
    name="fcp_read_throughput",
    title=Title("FCP read throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_fcp_write_throughput = metrics.Metric(
    name="fcp_write_throughput",
    title=Title("FCP write throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_fcp_other_ops = metrics.Metric(
    name="fcp_other_ops",
    title=Title("FCP other ops"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_iscsi_other_data = metrics.Metric(
    name="iscsi_other_data",
    title=Title("ISCSI other data"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
metric_iscsi_other_latency = metrics.Metric(
    name="iscsi_other_latency",
    title=Title("ISCSI other latency"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)
metric_iscsi_read_ios = metrics.Metric(
    name="iscsi_read_ios",
    title=Title("ISCSI read ios"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_iscsi_write_ios = metrics.Metric(
    name="iscsi_write_ios",
    title=Title("ISCSI write ios"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_iscsi_read_throughput = metrics.Metric(
    name="iscsi_read_throughput",
    title=Title("ISCSI read throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_iscsi_write_throughput = metrics.Metric(
    name="iscsi_write_throughput",
    title=Title("ISCSI write throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_iscsi_other_ops = metrics.Metric(
    name="iscsi_other_ops",
    title=Title("ISCSI other ops"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_fan_speed = metrics.Metric(
    name="fan_speed",
    title=Title("Fan speed"),
    unit=UNIT_REVOLUTIONS_PER_MINUTE,
    color=metrics.Color.ORANGE,
)
metric_process_handles = metrics.Metric(
    name="process_handles",
    title=Title("Process handles"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
