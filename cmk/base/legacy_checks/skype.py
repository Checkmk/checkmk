#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="arg-type"
# mypy: disable-error-code="type-arg"

from cmk.agent_based.legacy.v0_unstable import (
    check_levels,
    LegacyCheckDefinition,
    LegacyCheckResult,
)
from cmk.agent_based.v2 import render, StringTable
from cmk.base.check_legacy_includes.wmi import (
    get_levels_quadruple,
    inventory_wmi_table_instances,
    inventory_wmi_table_total,
    wmi_calculate_raw_average,
    wmi_calculate_raw_average_time,
    wmi_yield_raw_counter,
    wmi_yield_raw_persec,
)
from cmk.plugins.windows.agent_based.libwmi import parse_wmi_table, WMISection, WMITable

check_info = {}


def _wmi_yield_raw_average(
    table: WMITable,
    row: str | int,
    column: str,
    infoname: str | None,
    perfvar: str | None,
    levels: tuple | dict[str, tuple] | None = None,
    perfscale: float = 1.0,
) -> LegacyCheckResult:
    try:
        average = wmi_calculate_raw_average(table, row, column, 1) * perfscale
    except KeyError:
        return

    yield check_levels(
        average,
        perfvar,
        get_levels_quadruple(levels),
        infoname=infoname,
        human_readable_func=render.time_offset,
    )


def _wmi_yield_raw_average_timer(
    table: WMITable,
    row: str | int,
    column: str,
    infoname: str | None,
    perfvar: str | None,
    levels: tuple | dict[str, tuple] | None = None,
) -> LegacyCheckResult:
    assert table.frequency
    try:
        average = (
            wmi_calculate_raw_average_time(
                table,
                row,
                column,
            )
            / table.frequency
        )
    except KeyError:
        return

    yield check_levels(
        average,
        perfvar,
        get_levels_quadruple(levels),
        infoname=infoname,
    )


def parse_skype(string_table: StringTable) -> WMISection:
    return parse_wmi_table(string_table, key="instance")


def check_skype(_no_item, params, parsed):
    # LS:WEB - Address Book Web Query\WEB - Failed search requests/sec
    # LS:WEB - Location Information Service\WEB - Failed Get Locations Requests/Second
    # LS:WEB - Distribution List Expansion\WEB - Timed out Active Directory Requests/sec
    # LS:WEB - UCWA\UCWA - HTTP 5xx Responses/Second
    # ASP.NET Apps v4.0.30319(*)\Requests Rejected
    #
    # LS:WEB - Address Book File Download\WEB – Failed File Requests/Second
    # LS: JoinLauncher – Join Launcher Service Failures\JOINLAUNCHER – Join Failures
    # LS:WEB – Auth Provider related calls\WEB – Failed validate cert calls to the cert auth provider

    yield from wmi_yield_raw_persec(
        parsed.get("LS:WEB - Address Book Web Query"),
        None,
        "WEB - Failed search requests/sec",
        infoname="Failed search requests/sec",
        perfvar="failed_search_requests",
        levels=params["failed_search_requests"],
    )

    yield from wmi_yield_raw_persec(
        parsed.get("LS:WEB - Location Information Service"),
        None,
        "WEB - Failed Get Locations Requests/Second",
        infoname="Failed location requests/sec",
        perfvar="failed_location_requests",
        levels=params["failed_locations_requests"],
    )

    yield from wmi_yield_raw_persec(
        parsed.get("LS:WEB - Distribution List Expansion"),
        None,
        "WEB - Timed out Active Directory Requests/sec",
        infoname="Timeout AD requests/sec",
        perfvar="failed_ad_requests",
        levels=params["timedout_ad_requests"],
    )

    yield from wmi_yield_raw_persec(
        parsed.get("LS:WEB - UCWA"),
        None,
        "UCWA - HTTP 5xx Responses/Second",
        infoname="HTTP 5xx/sec",
        perfvar="http_5xx",
        levels=params["5xx_responses"],
    )

    yield from wmi_yield_raw_counter(
        parsed.get("ASP.NET Apps v4.0.30319"),
        None,
        "Requests Rejected",
        infoname="Requests rejected",
        perfvar="asp_requests_rejected",
        levels=params["asp_requests_rejected"],
    )

    if "LS:WEB - Address Book File Download" in parsed:
        yield from wmi_yield_raw_persec(
            parsed.get("LS:WEB - Address Book File Download"),
            None,
            "WEB - Failed File Requests/Second",
            infoname="Failed file requests/sec",
            perfvar="failed_file_requests",
            levels=params["failed_file_requests"],
        )

    if "LS:JoinLauncher - Join Launcher Service Failures" in parsed:
        yield from wmi_yield_raw_counter(
            parsed.get("LS:JoinLauncher - Join Launcher Service Failures"),
            None,
            "JOINLAUNCHER - Join failures",
            infoname="Join failures",
            perfvar="join_failures",
            levels=params["join_failures"],
        )

    if "LS:WEB - Auth Provider related calls" in parsed:
        yield from wmi_yield_raw_counter(
            parsed.get("LS:WEB - Auth Provider related calls"),
            None,
            "WEB - Failed validate cert calls to the cert auth provider",
            infoname="Failed cert validations",
            perfvar="failed_validate_cert_calls",
            levels=params["failed_validate_cert"],
        )


def discover_skype(table):
    return inventory_wmi_table_total(
        table,
        required_tables=[
            "LS:WEB - Address Book Web Query",
            "LS:WEB - Location Information Service",
            "LS:WEB - Distribution List Expansion",
            "LS:WEB - UCWA",
            "ASP.NET Apps v4.0.30319",
        ],
    )


check_info["skype"] = LegacyCheckDefinition(
    name="skype",
    parse_function=parse_skype,
    service_name="Skype Web Components",
    discovery_function=discover_skype,
    check_function=check_skype,
    check_ruleset_name="skype",
    # these defaults were specified by customer,
    check_default_parameters={
        "failed_search_requests": {"upper": (1.0, 2.0)},
        "failed_locations_requests": {"upper": (1.0, 2.0)},
        "timedout_ad_requests": {"upper": (0.01, 0.02)},
        "5xx_responses": {"upper": (1.0, 2.0)},
        "asp_requests_rejected": {"upper": (1, 2)},
        "failed_file_requests": {"upper": (1.0, 2.0)},
        "join_failures": {"upper": (1, 2)},
        "failed_validate_cert": {"upper": (1, 2)},
    },
)


def check_skype_mcu(_no_item, _no_params, parsed):
    # LS:DATAMCU - MCU Health And Performance\DATAMCU - MCU Health State
    # LS:AVMCU - MCU Health And Performance\AVMCU - MCU Health State
    # LS:AsMcu - MCU Health And Performance\ASMCU - MCU Health State
    # LS:ImMcu - MCU Health And Performance\IMMCU - MCU Health State

    def health(value, label):
        # The current health of the MCU. 0 = Normal. 1 = Loaded. 2 = Full. 3 = Unavailable.
        state = {
            "0": (0, "Normal"),
            "1": (1, "Loaded"),
            "2": (1, "Full"),
            "3": (2, "Unavailable"),
        }.get(value, (2, "unknown (%s)" % value))

        return state[0], f"{label}: {state[1]}"

    yield health(
        parsed["LS:DATAMCU - MCU Health And Performance"].get(0, "DATAMCU - MCU Health State"),
        "DATAMCU",
    )

    yield health(
        parsed["LS:AVMCU - MCU Health And Performance"].get(0, "AVMCU - MCU Health State"), "AVMCU"
    )

    yield health(
        parsed["LS:AsMcu - MCU Health And Performance"].get(0, "ASMCU - MCU Health State"), "ASMCU"
    )

    yield health(
        parsed["LS:ImMcu - MCU Health And Performance"].get(0, "IMMCU - MCU Health State"), "IMMCU"
    )


def discover_skype_mcu(parsed):
    return inventory_wmi_table_total(
        parsed,
        required_tables=[
            "LS:DATAMCU - MCU Health And Performance",
            "LS:AVMCU - MCU Health And Performance",
            "LS:AsMcu - MCU Health And Performance",
            "LS:ImMcu - MCU Health And Performance",
        ],
    )


check_info["skype.mcu"] = LegacyCheckDefinition(
    name="skype_mcu",
    service_name="Skype MCU Health",
    sections=["skype"],
    discovery_function=discover_skype_mcu,
    check_function=check_skype_mcu,
)


def check_skype_conferencing(_no_item, params, parsed):
    # LS:CAA - Operations\CAA - Incomplete calls per sec
    # LS:USrv - Conference Mcu Allocator\USrv - Create Conference Latency (msec)
    # LS:USrv - Conference Mcu Allocator\USrv – Allocation Latency (msec)

    yield from wmi_yield_raw_persec(
        parsed.get("LS:CAA - Operations"),
        None,
        "CAA - Incomplete calls per sec",
        infoname="Incomplete calls/sec",
        perfvar="caa_incomplete_calls",
        levels=params["incomplete_calls"],
    )

    yield from _wmi_yield_raw_average(
        parsed.get("LS:USrv - Conference Mcu Allocator"),
        None,
        "USrv - Create Conference Latency (msec)",
        infoname="Create conference latency",
        perfvar="usrv_create_conference_latency",
        levels=params["create_conference_latency"],
    )

    yield from _wmi_yield_raw_average(
        parsed.get("LS:USrv - Conference Mcu Allocator"),
        None,
        "USrv - Allocation Latency (msec)",
        infoname="Allocation latency",
        perfvar="usrv_allocation_latency",
        levels=params["allocation_latency"],
    )


def discover_skype_conferencing(table):
    return inventory_wmi_table_total(
        table,
        required_tables=[
            "LS:CAA - Operations",
            "LS:USrv - Conference Mcu Allocator",
        ],
    )


check_info["skype.conferencing"] = LegacyCheckDefinition(
    name="skype_conferencing",
    service_name="Skype Conferencing",
    sections=["skype"],
    discovery_function=discover_skype_conferencing,
    check_function=check_skype_conferencing,
    check_ruleset_name="skype_conferencing",
    check_default_parameters={
        "incomplete_calls": {"upper": (20.0, 40.0)},
        "create_conference_latency": {"upper": (5000.0, 10000.0)},
        "allocation_latency": {"upper": (5000.0, 10000.0)},
    },
)


def discover_skype_sip_stack(parsed):
    return inventory_wmi_table_total(
        parsed,
        required_tables=[
            "LS:SIP - Protocol",
            "LS:USrv - DBStore",
            "LS:SIP - Responses",
            "LS:SIP - Load Management",
            "LS:SIP - Peers",
        ],
    )


def check_skype_sip_stack(_no_item, params, parsed):
    # LS:SIP - Protocol\SIP - Average Incoming Message Processing Time
    # LS:SIP - Protocol\SIP - Incoming Responses Dropped /Sec
    # LS:SIP - Protocol\SIP - Incoming Requests Dropped /Sec
    # LS:USrv - DBStore\USrv - Queue Latency (msec)
    # LS:USrv - DBStore\USrv - Sproc Latency (msec)
    # LS:USrv - DBStore\USrv - Throttled requests/sec

    # LS:SIP - Responses\SIP - Local 503 Responses/sec
    # LS:SIP - Load Management\SIP - Incoming Messages Timed out
    # LS:SIP - Load Management\SIP - Average Holding Time For Incoming Messages
    # LS:SIP - Peers\SIP - Flow-controlled Connections
    # LS:SIP - Peers\SIP - Average Outgoing Queue Delay
    # LS:SIP - Peers(*)\SIP-Sends Timed-Out/sec
    yield from _wmi_yield_raw_average_timer(
        parsed.get("LS:SIP - Protocol"),
        None,
        "SIP - Average Incoming Message Processing Time",
        infoname="Avg incoming message processing time",
        perfvar="sip_message_processing_time",
        levels=params["message_processing_time"],
    )

    yield from wmi_yield_raw_persec(
        parsed.get("LS:SIP - Protocol"),
        None,
        "SIP - Incoming Responses Dropped /Sec",
        infoname="Incoming responses dropped/sec",
        perfvar="sip_incoming_responses_dropped",
        levels=params["incoming_responses_dropped"],
    )

    yield from wmi_yield_raw_persec(
        parsed.get("LS:SIP - Protocol"),
        None,
        "SIP - Incoming Requests Dropped /Sec",
        infoname="Incoming requests dropped/sec",
        perfvar="sip_incoming_requests_dropped",
        levels=params["incoming_requests_dropped"],
    )

    yield from _wmi_yield_raw_average(
        parsed.get("LS:USrv - DBStore"),
        None,
        "USrv - Queue Latency (msec)",
        infoname="Queue latency",
        perfvar="usrv_queue_latency",
        perfscale=0.001,
        levels=params["queue_latency"],
    )

    yield from _wmi_yield_raw_average(
        parsed.get("LS:USrv - DBStore"),
        None,
        "USrv - Sproc Latency (msec)",
        infoname="Sproc latency",
        perfvar="usrv_sproc_latency",
        perfscale=0.001,
        levels=params["sproc_latency"],
    )

    yield from wmi_yield_raw_persec(
        parsed.get("LS:USrv - DBStore"),
        None,
        "USrv - Throttled requests/sec",
        infoname="Throttled requests/sec",
        perfvar="usrv_throttled_requests",
        levels=params["throttled_requests"],
    )

    yield from wmi_yield_raw_persec(
        parsed.get("LS:SIP - Responses"),
        None,
        "SIP - Local 503 Responses /Sec",
        infoname="Local 503 responses/sec",
        perfvar="sip_503_responses",
        levels=params["local_503_responses"],
    )

    yield from wmi_yield_raw_counter(
        parsed.get("LS:SIP - Load Management"),
        None,
        "SIP - Incoming Messages Timed out",
        infoname="Incoming messages timed out",
        perfvar="sip_incoming_messages_timed_out",
        levels=params["timedout_incoming_messages"],
    )

    yield from _wmi_yield_raw_average_timer(
        parsed.get("LS:SIP - Load Management"),
        None,
        "SIP - Average Holding Time For Incoming Messages",
        infoname="Avg holding time for incoming messages",
        perfvar="sip_avg_holding_time_incoming_messages",
        levels=params["holding_time_incoming"],
    )

    yield from wmi_yield_raw_counter(
        parsed.get("LS:SIP - Peers"),
        None,
        "SIP - Flow-controlled Connections",
        infoname="Flow-controlled connections",
        perfvar="sip_flow_controlled_connections",
        levels=params["flow_controlled_connections"],
    )

    yield from _wmi_yield_raw_average_timer(
        parsed.get("LS:SIP - Peers"),
        None,
        "SIP - Average Outgoing Queue Delay",
        infoname="Avg outgoing queue delay",
        perfvar="sip_avg_outgoing_queue_delay",
        levels=params["outgoing_queue_delay"],
    )

    yield from wmi_yield_raw_persec(
        parsed.get("LS:SIP - Peers"),
        None,
        "SIP - Sends Timed-Out /Sec",
        infoname="Sends timed out/sec",
        perfvar="sip_sends_timed_out",
        levels=params["timedout_sends"],
    )

    if "LS:SIP - Authentication" in parsed:
        yield from wmi_yield_raw_persec(
            parsed.get("LS:SIP - Authentication"),
            None,
            "SIP - Authentication System Errors /Sec",
            infoname="Authentication errors/sec",
            perfvar="sip_authentication_errors",
            levels=params["authentication_errors"],
        )


check_info["skype.sip_stack"] = LegacyCheckDefinition(
    name="skype_sip_stack",
    service_name="Skype SIP Stack",
    sections=["skype"],
    discovery_function=discover_skype_sip_stack,
    check_function=check_skype_sip_stack,
    check_ruleset_name="skype_sip",
    check_default_parameters={
        "message_processing_time": {"upper": (1.0, 2.0)},  # for edge servers: < 3
        "incoming_responses_dropped": {"upper": (1.0, 2.0)},
        "incoming_requests_dropped": {"upper": (1.0, 2.0)},
        "queue_latency": {"upper": (0.1, 0.2)},
        "sproc_latency": {"upper": (0.1, 0.2)},
        "throttled_requests": {"upper": (0.2, 0.4)},
        "local_503_responses": {"upper": (0.01, 0.02)},
        "timedout_incoming_messages": {"upper": (2, 4)},
        "holding_time_incoming": {"upper": (6.0, 12.0)},
        "flow_controlled_connections": {"upper": (1, 2)},
        "outgoing_queue_delay": {"upper": (2.0, 4.0)},
        "timedout_sends": {"upper": (0.01, 0.02)},
        "authentication_errors": {"upper": (1.0, 2.0)},
    },
)


def check_skype_mediation_server(_no_item, params, parsed):
    # LS:MediationServer - Health Indices\- Load Call Failure Index
    # LS:MediationServer - Global Counters\- Total failed calls caused by unexpected interaction from the Proxy
    # LS:MediationServer - Global Per Gateway Counters(*)\- Total failed calls caused by unexpected interaction from a gateway
    # LS:MediationServer - Media Relay\- Media Connectivity Check Failure

    yield from wmi_yield_raw_counter(
        parsed.get("LS:MediationServer - Health Indices"),
        None,
        "- Load Call Failure Index",
        infoname="Load call failure index",
        perfvar="mediation_load_call_failure_index",
        levels=params["load_call_failure_index"],
    )

    yield from wmi_yield_raw_counter(
        parsed.get("LS:MediationServer - Global Counters"),
        None,
        "- Total failed calls caused by unexpected interaction from the Proxy",
        infoname="Failed calls because of proxy",
        perfvar="mediation_failed_calls_because_of_proxy",
        levels=params["failed_calls_because_of_proxy"],
    )

    yield from wmi_yield_raw_counter(
        parsed.get("LS:MediationServer - Global Per Gateway Counters"),
        None,
        "- Total failed calls caused by unexpected interaction from a gateway",
        infoname="Failed calls because of gateway",
        perfvar="mediation_failed_calls_because_of_gateway",
        levels=params["failed_calls_because_of_gateway"],
    )

    yield from wmi_yield_raw_counter(
        parsed.get("LS:MediationServer - Media Relay"),
        None,
        "- Media Connectivity Check Failure",
        infoname="Media connectivity check failure",
        perfvar="mediation_media_connectivity_failure",
        levels=params["media_connectivity_failure"],
    )


def discover_skype_mediation_server(parsed):
    return inventory_wmi_table_total(
        parsed,
        required_tables=[
            "LS:MediationServer - Health Indices",
            "LS:MediationServer - Global Counters",
            "LS:MediationServer - Global Per Gateway Counters",
            "LS:MediationServer - Media Relay",
        ],
    )


check_info["skype.mediation_server"] = LegacyCheckDefinition(
    name="skype_mediation_server",
    service_name="Skype Mediation Server",
    sections=["skype"],
    discovery_function=discover_skype_mediation_server,
    check_function=check_skype_mediation_server,
    check_ruleset_name="skype_mediation_server",
    check_default_parameters={
        "load_call_failure_index": {"upper": (10, 20)},
        "failed_calls_because_of_proxy": {"upper": (10, 20)},
        "failed_calls_because_of_gateway": {"upper": (10, 20)},
        "media_connectivity_failure": {"upper": (1, 2)},
    },
)


def check_skype_edge_auth(_no_item, params, parsed):
    # LS:A/V Auth - Requests\- Bad Requests Received/sec
    yield from wmi_yield_raw_persec(
        parsed.get("LS:A/V Auth - Requests"),
        None,
        "- Bad Requests Received/sec",
        infoname="Bad requests/sec",
        perfvar="avauth_failed_requests",
        levels=params["bad_requests"],
    )


def discover_skype_edge_auth(parsed):
    return inventory_wmi_table_total(parsed, required_tables=["LS:A/V Auth - Requests"])


check_info["skype.edge_auth"] = LegacyCheckDefinition(
    name="skype_edge_auth",
    service_name="Skype Edge Authentification",
    sections=["skype"],
    discovery_function=discover_skype_edge_auth,
    check_function=check_skype_edge_auth,
    check_ruleset_name="skype_edgeauth",
    check_default_parameters={
        "bad_requests": {"upper": (20, 40)},
    },
)


def check_skype_av_edge(item, params, parsed):
    # LS:A/V Edge - UDP Counters(*)\A/V Edge - Authentication Failures/sec
    # LS:A/V Edge - TCP Counters(*)\A/V Edge - Authentication Failures/sec
    # LS:A/V Edge - UDP Counters(*)\A/V Edge - Allocate Requests Exceeding Port Limit
    # LS:A/V Edge - TCP Counters(*)\A/V Edge - Allocate Requests Exceeding Port Limit
    # LS:A/V Edge - UDP Counters(*)\A/V Edge - Packets Dropped/sec
    # LS:A/V Edge - TCP Counters(*)\A/V Edge - Packets Dropped/sec
    yield from wmi_yield_raw_persec(
        parsed.get("LS:A/V Edge - UDP Counters"),
        item,
        "A/V Edge - Authentication Failures/sec",
        infoname="UDP auth failures/sec",
        perfvar="edge_udp_failed_auth",
        levels=params["authentication_failures"],
    )

    yield from wmi_yield_raw_persec(
        parsed.get("LS:A/V Edge - TCP Counters"),
        item,
        "A/V Edge - Authentication Failures/sec",
        infoname="TCP auth failures/sec",
        perfvar="edge_tcp_failed_auth",
        levels=params["authentication_failures"],
    )

    yield from wmi_yield_raw_persec(
        parsed.get("LS:A/V Edge - UDP Counters"),
        item,
        "A/V Edge - Allocate Requests Exceeding Port Limit/sec",
        infoname="UDP allocate requests > port limit/sec",
        perfvar="edge_udp_allocate_requests_exceeding_port_limit",
        levels=params["allocate_requests_exceeding"],
    )

    yield from wmi_yield_raw_persec(
        parsed.get("LS:A/V Edge - TCP Counters"),
        item,
        "A/V Edge - Allocate Requests Exceeding Port Limit/sec",
        infoname="TCP allocate requests > port limit/sec",
        perfvar="edge_tcp_allocate_requests_exceeding_port_limit",
        levels=params["allocate_requests_exceeding"],
    )

    yield from wmi_yield_raw_persec(
        parsed.get("LS:A/V Edge - UDP Counters"),
        item,
        "A/V Edge - Packets Dropped/sec",
        infoname="UDP packets dropped/sec",
        perfvar="edge_udp_packets_dropped",
        levels=params["packets_dropped"],
    )

    yield from wmi_yield_raw_persec(
        parsed.get("LS:A/V Edge - TCP Counters"),
        item,
        "A/V Edge - Packets Dropped/sec",
        infoname="TCP packets dropped/sec",
        perfvar="edge_tcp_packets_dropped",
        levels=params["packets_dropped"],
    )


def discover_skype_edge(parsed):
    return inventory_wmi_table_instances(
        parsed, required_tables=["LS:A/V Edge - TCP Counters", "LS:A/V Edge - UDP Counters"]
    )


check_info["skype.edge"] = LegacyCheckDefinition(
    name="skype_edge",
    service_name="Skype AV Edge %s",
    sections=["skype"],
    discovery_function=discover_skype_edge,
    check_function=check_skype_av_edge,
    check_ruleset_name="skype_edge",
    check_default_parameters={
        "authentication_failures": {"upper": (20, 40)},
        "allocate_requests_exceeding": {"upper": (20, 40)},
        "packets_dropped": {"upper": (200, 400)},
    },
)


def check_skype_data_proxy(item, params, parsed):
    # LS:DATAPROXY - Server Connections(*)\DATAPROXY - Current count of server connections that are throttled
    # LS:DATAPROXY - Server Connections(*)\DATAPROXY - System is throttling
    yield from wmi_yield_raw_counter(
        parsed.get("LS:DATAPROXY - Server Connections"),
        item,
        "DATAPROXY - Current count of server connections that are throttled",
        infoname="Server connections throttled",
        perfvar="dataproxy_connections_throttled",
        levels=params["throttled_connections"],
    )

    throttling = int(
        parsed["LS:DATAPROXY - Server Connections"].get(0, "DATAPROXY - System is throttling")
    )

    if throttling != 0:
        yield 2, "System is throttling"


def discover_skype_data_proxy(parsed):
    return inventory_wmi_table_instances(
        parsed, required_tables=["LS:DATAPROXY - Server Connections"]
    )


check_info["skype.data_proxy"] = LegacyCheckDefinition(
    name="skype_data_proxy",
    service_name="Skype Data Proxy %s",
    sections=["skype"],
    discovery_function=discover_skype_data_proxy,
    check_function=check_skype_data_proxy,
    check_ruleset_name="skype_proxy",
    check_default_parameters={
        "throttled_connections": {"upper": (1, 2)},
    },
)


def check_skype_xmpp_proxy(_no_item, params, parsed):
    # LS:XmppFederationProxy - Streams\XmppFederationProxy - Failed outbound stream establishes/sec
    # LS:XmppFederationProxy - Streams\XmppFederationProxy - Failed inbound stream establishes/sec
    yield from wmi_yield_raw_persec(
        parsed.get("LS:XmppFederationProxy - Streams"),
        None,
        "XmppFederationProxy - Failed outbound stream establishes/sec",
        infoname="Failed outbound streams",
        perfvar="xmpp_failed_outbound_streams",
        levels=params["failed_outbound_streams"],
    )

    yield from wmi_yield_raw_persec(
        parsed.get("LS:XmppFederationProxy - Streams"),
        None,
        "XmppFederationProxy - Failed inbound stream establishes/sec",
        infoname="Failed inbound streams",
        perfvar="xmpp_failed_inbound_streams",
        levels=params["failed_inbound_streams"],
    )


def discover_skype_xmpp_proxy(parsed):
    return inventory_wmi_table_total(parsed, required_tables=["LS:XmppFederationProxy - Streams"])


check_info["skype.xmpp_proxy"] = LegacyCheckDefinition(
    name="skype_xmpp_proxy",
    service_name="Skype XMPP Proxy",
    sections=["skype"],
    discovery_function=discover_skype_xmpp_proxy,
    check_function=check_skype_xmpp_proxy,
    check_ruleset_name="skype_xmpp",
    check_default_parameters={
        "failed_outbound_streams": {"upper": (0.01, 0.02)},
        "failed_inbound_streams": {"upper": (0.01, 0.02)},
    },
)


def check_skype_mobile(_no_item, params, parsed):
    # LS:WEB - UCWA
    # LS:WEB - Throttling and Authentication\WEB - Total Requests in Processing

    ucwa_table = parsed.get("LS:WEB - UCWA")
    if ucwa_table is None:
        return

    for instance, name in [
        ("AndroidLync", "Android"),
        ("iPadLync", "iPad"),
        ("iPhoneLync", "iPhone"),
        ("LyncForMac", "Mac"),
    ]:
        try:
            value = int(ucwa_table.get(instance, "UCWA - Active Session Count"))
        except KeyError:
            continue
        yield 0, f"{name}: {value} active", [("ucwa_active_sessions_%s" % name.lower(), value)]

    yield from wmi_yield_raw_counter(
        parsed.get("LS:WEB - Throttling and Authentication"),
        None,
        "WEB - Total Requests In Processing",
        infoname="Requested",
        perfvar="web_requests_processing",
        levels=params["requests_processing"],
    )


def discover_skype_mobile(parsed):
    return inventory_wmi_table_total(
        parsed,
        required_tables=[
            "LS:WEB - UCWA",
            "LS:WEB - Throttling and Authentication",
        ],
    )


check_info["skype.mobile"] = LegacyCheckDefinition(
    name="skype_mobile",
    service_name="Skype Mobile Sessions",
    sections=["skype"],
    discovery_function=discover_skype_mobile,
    check_function=check_skype_mobile,
    check_ruleset_name="skype_mobile",
    check_default_parameters={"requests_processing": {"upper": (10000, 20000)}},
)
