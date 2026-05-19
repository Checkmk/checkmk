#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.windows.agent_based.libwmi import (
    get_wmi_time,
    parse_wmi_table,
    WMISection,
    WMITable,
)
from cmk.plugins.windows.agent_based.libwmi_legacy import (
    inventory_wmi_table_instances,
    inventory_wmi_table_total,
    wmi_calculate_raw_average,
    wmi_calculate_raw_average_time,
)


def _levels_upper(levels: Mapping[str, tuple[float, float]] | None) -> tuple[float, float] | None:
    if not levels:
        return None
    return levels.get("upper")


def _wmi_yield_raw_persec(
    table: WMITable | None,
    row: str | int | None,
    column: str,
    label: str,
    perfvar: str,
    levels: Mapping[str, tuple[float, float]] | None,
) -> CheckResult:
    if table is None:
        return
    if row == "" or row is None:
        row = 0
    try:
        value = table.get(row, column)
        assert value
    except KeyError:
        return

    value_per_sec = get_rate(
        get_value_store(),
        f"{column}_{table.name}",
        get_wmi_time(table, row),
        int(value),
        raise_overflow=True,
    )
    yield from check_levels_v1(
        value_per_sec,
        metric_name=perfvar,
        levels_upper=_levels_upper(levels),
        label=label,
    )


def _wmi_yield_raw_counter(
    table: WMITable | None,
    row: str | int | None,
    column: str,
    label: str,
    perfvar: str,
    levels: Mapping[str, tuple[float, float]] | None,
) -> CheckResult:
    if table is None:
        return
    if row == "" or row is None:
        row = 0
    try:
        value = table.get(row, column)
        assert value
    except KeyError:
        return

    yield from check_levels_v1(
        int(value),
        metric_name=perfvar,
        levels_upper=_levels_upper(levels),
        label=label,
        render_func=str,
    )


def _wmi_yield_raw_average(
    table: WMITable | None,
    row: str | int | None,
    column: str,
    label: str,
    perfvar: str,
    levels: Mapping[str, tuple[float, float]] | None = None,
    perfscale: float = 1.0,
) -> CheckResult:
    if table is None:
        return
    if row == "" or row is None:
        row = 0
    try:
        average = wmi_calculate_raw_average(table, row, column, 1) * perfscale
    except KeyError:
        return

    yield from check_levels_v1(
        average,
        metric_name=perfvar,
        levels_upper=_levels_upper(levels),
        label=label,
        render_func=render.time_offset,
    )


def _wmi_yield_raw_average_timer(
    table: WMITable | None,
    row: str | int | None,
    column: str,
    label: str,
    perfvar: str,
    levels: Mapping[str, tuple[float, float]] | None = None,
) -> CheckResult:
    if table is None:
        return
    assert table.frequency
    if row == "" or row is None:
        row = 0
    try:
        average = wmi_calculate_raw_average_time(table, row, column) / table.frequency
    except KeyError:
        return

    yield from check_levels_v1(
        average,
        metric_name=perfvar,
        levels_upper=_levels_upper(levels),
        label=label,
    )


def parse_skype(string_table: StringTable) -> WMISection:
    return parse_wmi_table(string_table, key="instance")


def discover_skype(section: WMISection) -> DiscoveryResult:
    for item, _params in inventory_wmi_table_total(
        section,
        required_tables=[
            "LS:WEB - Address Book Web Query",
            "LS:WEB - Location Information Service",
            "LS:WEB - Distribution List Expansion",
            "LS:WEB - UCWA",
            "ASP.NET Apps v4.0.30319",
        ],
    ):
        yield Service(item=item)


def check_skype(params: Mapping[str, Any], section: WMISection) -> CheckResult:
    # LS:WEB - Address Book Web Query\WEB - Failed search requests/sec
    # LS:WEB - Location Information Service\WEB - Failed Get Locations Requests/Second
    # LS:WEB - Distribution List Expansion\WEB - Timed out Active Directory Requests/sec
    # LS:WEB - UCWA\UCWA - HTTP 5xx Responses/Second
    # ASP.NET Apps v4.0.30319(*)\Requests Rejected

    yield from _wmi_yield_raw_persec(
        section.get("LS:WEB - Address Book Web Query"),
        None,
        "WEB - Failed search requests/sec",
        label="Failed search requests/sec",
        perfvar="failed_search_requests",
        levels=params["failed_search_requests"],
    )

    yield from _wmi_yield_raw_persec(
        section.get("LS:WEB - Location Information Service"),
        None,
        "WEB - Failed Get Locations Requests/Second",
        label="Failed location requests/sec",
        perfvar="failed_location_requests",
        levels=params["failed_locations_requests"],
    )

    yield from _wmi_yield_raw_persec(
        section.get("LS:WEB - Distribution List Expansion"),
        None,
        "WEB - Timed out Active Directory Requests/sec",
        label="Timeout AD requests/sec",
        perfvar="failed_ad_requests",
        levels=params["timedout_ad_requests"],
    )

    yield from _wmi_yield_raw_persec(
        section.get("LS:WEB - UCWA"),
        None,
        "UCWA - HTTP 5xx Responses/Second",
        label="HTTP 5xx/sec",
        perfvar="http_5xx",
        levels=params["5xx_responses"],
    )

    yield from _wmi_yield_raw_counter(
        section.get("ASP.NET Apps v4.0.30319"),
        None,
        "Requests Rejected",
        label="Requests rejected",
        perfvar="asp_requests_rejected",
        levels=params["asp_requests_rejected"],
    )

    if "LS:WEB - Address Book File Download" in section:
        yield from _wmi_yield_raw_persec(
            section.get("LS:WEB - Address Book File Download"),
            None,
            "WEB - Failed File Requests/Second",
            label="Failed file requests/sec",
            perfvar="failed_file_requests",
            levels=params["failed_file_requests"],
        )

    if "LS:JoinLauncher - Join Launcher Service Failures" in section:
        yield from _wmi_yield_raw_counter(
            section.get("LS:JoinLauncher - Join Launcher Service Failures"),
            None,
            "JOINLAUNCHER - Join failures",
            label="Join failures",
            perfvar="join_failures",
            levels=params["join_failures"],
        )

    if "LS:WEB - Auth Provider related calls" in section:
        yield from _wmi_yield_raw_counter(
            section.get("LS:WEB - Auth Provider related calls"),
            None,
            "WEB - Failed validate cert calls to the cert auth provider",
            label="Failed cert validations",
            perfvar="failed_validate_cert_calls",
            levels=params["failed_validate_cert"],
        )


agent_section_skype = AgentSection(
    name="skype",
    parse_function=parse_skype,
)


check_plugin_skype = CheckPlugin(
    name="skype",
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


_MCU_HEALTH = {
    "0": (State.OK, "Normal"),
    "1": (State.WARN, "Loaded"),
    "2": (State.WARN, "Full"),
    "3": (State.CRIT, "Unavailable"),
}


def _mcu_health(value: str | None, label: str) -> Result:
    state, text = _MCU_HEALTH.get(value or "", (State.CRIT, f"unknown ({value})"))
    return Result(state=state, summary=f"{label}: {text}")


def discover_skype_mcu(section: WMISection) -> DiscoveryResult:
    for item, _params in inventory_wmi_table_total(
        section,
        required_tables=[
            "LS:DATAMCU - MCU Health And Performance",
            "LS:AVMCU - MCU Health And Performance",
            "LS:AsMcu - MCU Health And Performance",
            "LS:ImMcu - MCU Health And Performance",
        ],
    ):
        yield Service(item=item)


def check_skype_mcu(section: WMISection) -> CheckResult:
    yield _mcu_health(
        section["LS:DATAMCU - MCU Health And Performance"].get(0, "DATAMCU - MCU Health State"),
        "DATAMCU",
    )
    yield _mcu_health(
        section["LS:AVMCU - MCU Health And Performance"].get(0, "AVMCU - MCU Health State"),
        "AVMCU",
    )
    yield _mcu_health(
        section["LS:AsMcu - MCU Health And Performance"].get(0, "ASMCU - MCU Health State"),
        "ASMCU",
    )
    yield _mcu_health(
        section["LS:ImMcu - MCU Health And Performance"].get(0, "IMMCU - MCU Health State"),
        "IMMCU",
    )


check_plugin_skype_mcu = CheckPlugin(
    name="skype_mcu",
    service_name="Skype MCU Health",
    sections=["skype"],
    discovery_function=discover_skype_mcu,
    check_function=check_skype_mcu,
)


def discover_skype_conferencing(section: WMISection) -> DiscoveryResult:
    for item, _params in inventory_wmi_table_total(
        section,
        required_tables=[
            "LS:CAA - Operations",
            "LS:USrv - Conference Mcu Allocator",
        ],
    ):
        yield Service(item=item)


def check_skype_conferencing(params: Mapping[str, Any], section: WMISection) -> CheckResult:
    # LS:CAA - Operations\CAA - Incomplete calls per sec
    # LS:USrv - Conference Mcu Allocator\USrv - Create Conference Latency (msec)
    # LS:USrv - Conference Mcu Allocator\USrv – Allocation Latency (msec)

    yield from _wmi_yield_raw_persec(
        section.get("LS:CAA - Operations"),
        None,
        "CAA - Incomplete calls per sec",
        label="Incomplete calls/sec",
        perfvar="caa_incomplete_calls",
        levels=params["incomplete_calls"],
    )

    yield from _wmi_yield_raw_average(
        section.get("LS:USrv - Conference Mcu Allocator"),
        None,
        "USrv - Create Conference Latency (msec)",
        label="Create conference latency",
        perfvar="usrv_create_conference_latency",
        levels=params["create_conference_latency"],
    )

    yield from _wmi_yield_raw_average(
        section.get("LS:USrv - Conference Mcu Allocator"),
        None,
        "USrv - Allocation Latency (msec)",
        label="Allocation latency",
        perfvar="usrv_allocation_latency",
        levels=params["allocation_latency"],
    )


check_plugin_skype_conferencing = CheckPlugin(
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


def discover_skype_sip_stack(section: WMISection) -> DiscoveryResult:
    for item, _params in inventory_wmi_table_total(
        section,
        required_tables=[
            "LS:SIP - Protocol",
            "LS:USrv - DBStore",
            "LS:SIP - Responses",
            "LS:SIP - Load Management",
            "LS:SIP - Peers",
        ],
    ):
        yield Service(item=item)


def check_skype_sip_stack(params: Mapping[str, Any], section: WMISection) -> CheckResult:
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
        section.get("LS:SIP - Protocol"),
        None,
        "SIP - Average Incoming Message Processing Time",
        label="Avg incoming message processing time",
        perfvar="sip_message_processing_time",
        levels=params["message_processing_time"],
    )

    yield from _wmi_yield_raw_persec(
        section.get("LS:SIP - Protocol"),
        None,
        "SIP - Incoming Responses Dropped /Sec",
        label="Incoming responses dropped/sec",
        perfvar="sip_incoming_responses_dropped",
        levels=params["incoming_responses_dropped"],
    )

    yield from _wmi_yield_raw_persec(
        section.get("LS:SIP - Protocol"),
        None,
        "SIP - Incoming Requests Dropped /Sec",
        label="Incoming requests dropped/sec",
        perfvar="sip_incoming_requests_dropped",
        levels=params["incoming_requests_dropped"],
    )

    yield from _wmi_yield_raw_average(
        section.get("LS:USrv - DBStore"),
        None,
        "USrv - Queue Latency (msec)",
        label="Queue latency",
        perfvar="usrv_queue_latency",
        perfscale=0.001,
        levels=params["queue_latency"],
    )

    yield from _wmi_yield_raw_average(
        section.get("LS:USrv - DBStore"),
        None,
        "USrv - Sproc Latency (msec)",
        label="Sproc latency",
        perfvar="usrv_sproc_latency",
        perfscale=0.001,
        levels=params["sproc_latency"],
    )

    yield from _wmi_yield_raw_persec(
        section.get("LS:USrv - DBStore"),
        None,
        "USrv - Throttled requests/sec",
        label="Throttled requests/sec",
        perfvar="usrv_throttled_requests",
        levels=params["throttled_requests"],
    )

    yield from _wmi_yield_raw_persec(
        section.get("LS:SIP - Responses"),
        None,
        "SIP - Local 503 Responses /Sec",
        label="Local 503 responses/sec",
        perfvar="sip_503_responses",
        levels=params["local_503_responses"],
    )

    yield from _wmi_yield_raw_counter(
        section.get("LS:SIP - Load Management"),
        None,
        "SIP - Incoming Messages Timed out",
        label="Incoming messages timed out",
        perfvar="sip_incoming_messages_timed_out",
        levels=params["timedout_incoming_messages"],
    )

    yield from _wmi_yield_raw_average_timer(
        section.get("LS:SIP - Load Management"),
        None,
        "SIP - Average Holding Time For Incoming Messages",
        label="Avg holding time for incoming messages",
        perfvar="sip_avg_holding_time_incoming_messages",
        levels=params["holding_time_incoming"],
    )

    yield from _wmi_yield_raw_counter(
        section.get("LS:SIP - Peers"),
        None,
        "SIP - Flow-controlled Connections",
        label="Flow-controlled connections",
        perfvar="sip_flow_controlled_connections",
        levels=params["flow_controlled_connections"],
    )

    yield from _wmi_yield_raw_average_timer(
        section.get("LS:SIP - Peers"),
        None,
        "SIP - Average Outgoing Queue Delay",
        label="Avg outgoing queue delay",
        perfvar="sip_avg_outgoing_queue_delay",
        levels=params["outgoing_queue_delay"],
    )

    yield from _wmi_yield_raw_persec(
        section.get("LS:SIP - Peers"),
        None,
        "SIP - Sends Timed-Out /Sec",
        label="Sends timed out/sec",
        perfvar="sip_sends_timed_out",
        levels=params["timedout_sends"],
    )

    if "LS:SIP - Authentication" in section:
        yield from _wmi_yield_raw_persec(
            section.get("LS:SIP - Authentication"),
            None,
            "SIP - Authentication System Errors /Sec",
            label="Authentication errors/sec",
            perfvar="sip_authentication_errors",
            levels=params["authentication_errors"],
        )


check_plugin_skype_sip_stack = CheckPlugin(
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


def discover_skype_mediation_server(section: WMISection) -> DiscoveryResult:
    for item, _params in inventory_wmi_table_total(
        section,
        required_tables=[
            "LS:MediationServer - Health Indices",
            "LS:MediationServer - Global Counters",
            "LS:MediationServer - Global Per Gateway Counters",
            "LS:MediationServer - Media Relay",
        ],
    ):
        yield Service(item=item)


def check_skype_mediation_server(params: Mapping[str, Any], section: WMISection) -> CheckResult:
    # LS:MediationServer - Health Indices\- Load Call Failure Index
    # LS:MediationServer - Global Counters\- Total failed calls caused by unexpected interaction from the Proxy
    # LS:MediationServer - Global Per Gateway Counters(*)\- Total failed calls caused by unexpected interaction from a gateway
    # LS:MediationServer - Media Relay\- Media Connectivity Check Failure

    yield from _wmi_yield_raw_counter(
        section.get("LS:MediationServer - Health Indices"),
        None,
        "- Load Call Failure Index",
        label="Load call failure index",
        perfvar="mediation_load_call_failure_index",
        levels=params["load_call_failure_index"],
    )

    yield from _wmi_yield_raw_counter(
        section.get("LS:MediationServer - Global Counters"),
        None,
        "- Total failed calls caused by unexpected interaction from the Proxy",
        label="Failed calls because of proxy",
        perfvar="mediation_failed_calls_because_of_proxy",
        levels=params["failed_calls_because_of_proxy"],
    )

    yield from _wmi_yield_raw_counter(
        section.get("LS:MediationServer - Global Per Gateway Counters"),
        None,
        "- Total failed calls caused by unexpected interaction from a gateway",
        label="Failed calls because of gateway",
        perfvar="mediation_failed_calls_because_of_gateway",
        levels=params["failed_calls_because_of_gateway"],
    )

    yield from _wmi_yield_raw_counter(
        section.get("LS:MediationServer - Media Relay"),
        None,
        "- Media Connectivity Check Failure",
        label="Media connectivity check failure",
        perfvar="mediation_media_connectivity_failure",
        levels=params["media_connectivity_failure"],
    )


check_plugin_skype_mediation_server = CheckPlugin(
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


def discover_skype_edge_auth(section: WMISection) -> DiscoveryResult:
    for item, _params in inventory_wmi_table_total(
        section, required_tables=["LS:A/V Auth - Requests"]
    ):
        yield Service(item=item)


def check_skype_edge_auth(params: Mapping[str, Any], section: WMISection) -> CheckResult:
    # LS:A/V Auth - Requests\- Bad Requests Received/sec
    yield from _wmi_yield_raw_persec(
        section.get("LS:A/V Auth - Requests"),
        None,
        "- Bad Requests Received/sec",
        label="Bad requests/sec",
        perfvar="avauth_failed_requests",
        levels=params["bad_requests"],
    )


check_plugin_skype_edge_auth = CheckPlugin(
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


def discover_skype_edge(section: WMISection) -> DiscoveryResult:
    for item, _params in inventory_wmi_table_instances(
        section, required_tables=["LS:A/V Edge - TCP Counters", "LS:A/V Edge - UDP Counters"]
    ):
        yield Service(item=item)


def check_skype_av_edge(item: str, params: Mapping[str, Any], section: WMISection) -> CheckResult:
    # LS:A/V Edge - UDP Counters(*)\A/V Edge - Authentication Failures/sec
    # LS:A/V Edge - TCP Counters(*)\A/V Edge - Authentication Failures/sec
    # LS:A/V Edge - UDP Counters(*)\A/V Edge - Allocate Requests Exceeding Port Limit
    # LS:A/V Edge - TCP Counters(*)\A/V Edge - Allocate Requests Exceeding Port Limit
    # LS:A/V Edge - UDP Counters(*)\A/V Edge - Packets Dropped/sec
    # LS:A/V Edge - TCP Counters(*)\A/V Edge - Packets Dropped/sec
    yield from _wmi_yield_raw_persec(
        section.get("LS:A/V Edge - UDP Counters"),
        item,
        "A/V Edge - Authentication Failures/sec",
        label="UDP auth failures/sec",
        perfvar="edge_udp_failed_auth",
        levels=params["authentication_failures"],
    )

    yield from _wmi_yield_raw_persec(
        section.get("LS:A/V Edge - TCP Counters"),
        item,
        "A/V Edge - Authentication Failures/sec",
        label="TCP auth failures/sec",
        perfvar="edge_tcp_failed_auth",
        levels=params["authentication_failures"],
    )

    yield from _wmi_yield_raw_persec(
        section.get("LS:A/V Edge - UDP Counters"),
        item,
        "A/V Edge - Allocate Requests Exceeding Port Limit/sec",
        label="UDP allocate requests > port limit/sec",
        perfvar="edge_udp_allocate_requests_exceeding_port_limit",
        levels=params["allocate_requests_exceeding"],
    )

    yield from _wmi_yield_raw_persec(
        section.get("LS:A/V Edge - TCP Counters"),
        item,
        "A/V Edge - Allocate Requests Exceeding Port Limit/sec",
        label="TCP allocate requests > port limit/sec",
        perfvar="edge_tcp_allocate_requests_exceeding_port_limit",
        levels=params["allocate_requests_exceeding"],
    )

    yield from _wmi_yield_raw_persec(
        section.get("LS:A/V Edge - UDP Counters"),
        item,
        "A/V Edge - Packets Dropped/sec",
        label="UDP packets dropped/sec",
        perfvar="edge_udp_packets_dropped",
        levels=params["packets_dropped"],
    )

    yield from _wmi_yield_raw_persec(
        section.get("LS:A/V Edge - TCP Counters"),
        item,
        "A/V Edge - Packets Dropped/sec",
        label="TCP packets dropped/sec",
        perfvar="edge_tcp_packets_dropped",
        levels=params["packets_dropped"],
    )


check_plugin_skype_edge = CheckPlugin(
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


def discover_skype_data_proxy(section: WMISection) -> DiscoveryResult:
    for item, _params in inventory_wmi_table_instances(
        section, required_tables=["LS:DATAPROXY - Server Connections"]
    ):
        yield Service(item=item)


def check_skype_data_proxy(
    item: str, params: Mapping[str, Any], section: WMISection
) -> CheckResult:
    # LS:DATAPROXY - Server Connections(*)\DATAPROXY - Current count of server connections that are throttled
    # LS:DATAPROXY - Server Connections(*)\DATAPROXY - System is throttling
    yield from _wmi_yield_raw_counter(
        section.get("LS:DATAPROXY - Server Connections"),
        item,
        "DATAPROXY - Current count of server connections that are throttled",
        label="Server connections throttled",
        perfvar="dataproxy_connections_throttled",
        levels=params["throttled_connections"],
    )

    throttling_value = section["LS:DATAPROXY - Server Connections"].get(
        0, "DATAPROXY - System is throttling"
    )
    if throttling_value is not None and int(throttling_value) != 0:
        yield Result(state=State.CRIT, summary="System is throttling")


check_plugin_skype_data_proxy = CheckPlugin(
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


def discover_skype_xmpp_proxy(section: WMISection) -> DiscoveryResult:
    for item, _params in inventory_wmi_table_total(
        section, required_tables=["LS:XmppFederationProxy - Streams"]
    ):
        yield Service(item=item)


def check_skype_xmpp_proxy(params: Mapping[str, Any], section: WMISection) -> CheckResult:
    # LS:XmppFederationProxy - Streams\XmppFederationProxy - Failed outbound stream establishes/sec
    # LS:XmppFederationProxy - Streams\XmppFederationProxy - Failed inbound stream establishes/sec
    yield from _wmi_yield_raw_persec(
        section.get("LS:XmppFederationProxy - Streams"),
        None,
        "XmppFederationProxy - Failed outbound stream establishes/sec",
        label="Failed outbound streams",
        perfvar="xmpp_failed_outbound_streams",
        levels=params["failed_outbound_streams"],
    )

    yield from _wmi_yield_raw_persec(
        section.get("LS:XmppFederationProxy - Streams"),
        None,
        "XmppFederationProxy - Failed inbound stream establishes/sec",
        label="Failed inbound streams",
        perfvar="xmpp_failed_inbound_streams",
        levels=params["failed_inbound_streams"],
    )


check_plugin_skype_xmpp_proxy = CheckPlugin(
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


def discover_skype_mobile(section: WMISection) -> DiscoveryResult:
    for item, _params in inventory_wmi_table_total(
        section,
        required_tables=[
            "LS:WEB - UCWA",
            "LS:WEB - Throttling and Authentication",
        ],
    ):
        yield Service(item=item)


def check_skype_mobile(params: Mapping[str, Any], section: WMISection) -> CheckResult:
    # LS:WEB - UCWA
    # LS:WEB - Throttling and Authentication\WEB - Total Requests in Processing

    ucwa_table = section.get("LS:WEB - UCWA")
    if ucwa_table is None:
        return

    for instance, name in [
        ("AndroidLync", "Android"),
        ("iPadLync", "iPad"),
        ("iPhoneLync", "iPhone"),
        ("LyncForMac", "Mac"),
    ]:
        try:
            raw_value = ucwa_table.get(instance, "UCWA - Active Session Count")
        except KeyError:
            continue
        if raw_value is None:
            continue
        value = int(raw_value)
        yield from check_levels_v1(
            value,
            metric_name=f"ucwa_active_sessions_{name.lower()}",
            label=name,
            render_func=lambda v: f"{int(v)} active",
        )

    yield from _wmi_yield_raw_counter(
        section.get("LS:WEB - Throttling and Authentication"),
        None,
        "WEB - Total Requests In Processing",
        label="Requested",
        perfvar="web_requests_processing",
        levels=params["requests_processing"],
    )


check_plugin_skype_mobile = CheckPlugin(
    name="skype_mobile",
    service_name="Skype Mobile Sessions",
    sections=["skype"],
    discovery_function=discover_skype_mobile,
    check_function=check_skype_mobile,
    check_ruleset_name="skype_mobile",
    check_default_parameters={"requests_processing": {"upper": (10000, 20000)}},
)
