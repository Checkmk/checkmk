#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())
UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

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
    title=Title("HTTP 5xx errors per second"),
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
    title=Title("Mediation server - Load call failure index"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_mediation_failed_calls_because_of_proxy = metrics.Metric(
    name="mediation_failed_calls_because_of_proxy",
    title=Title("Mediation server - failed calls caused by unexpected interaction from proxy"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_mediation_failed_calls_because_of_gateway = metrics.Metric(
    name="mediation_failed_calls_because_of_gateway",
    title=Title("Mediation server - Failed calls caused by unexpected interaction of gateway"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_mediation_media_connectivity_failure = metrics.Metric(
    name="mediation_media_connectivity_failure",
    title=Title("Mediation server - Media connectivity check failure"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_avauth_failed_requests = metrics.Metric(
    name="avauth_failed_requests",
    title=Title("A/V Auth - bad requests received"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
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
