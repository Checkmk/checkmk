#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence

from .agent_based_api.v1 import register, Result, Service, State, type_defs
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils import interfaces, uptime

Section = Mapping[str, str]


def parse_fritz(string_table: type_defs.StringTable) -> Section:
    return {line[0]: ' '.join(line[1:]) for line in string_table if len(line) > 1}


register.agent_section(
    name="fritz",
    parse_function=parse_fritz,
)


#
# WAN Interface Check
#
def _section_to_interface(section: Section) -> interfaces.Section:
    link_stat = section.get('NewLinkStatus')
    if not link_stat:
        oper_status = '4'
    elif link_stat == 'Up':
        oper_status = '1'
    else:
        oper_status = '2'
    return [
        interfaces.Interface(
            index='0',
            descr='WAN',
            alias='WAN',
            type='6',
            speed=int(section.get('NewLayer1DownstreamMaxBitRate', 0)),
            oper_status=oper_status,
            in_octets=int(section.get('NewTotalBytesReceived', 0)),
            out_octets=int(section.get('NewTotalBytesSent', 0)),
        )
    ]


def discover_fritz_wan_if(
    params: Sequence[Mapping[str, Any]],
    section: Section,
) -> type_defs.DiscoveryResult:
    yield from interfaces.discover_interfaces(
        params,
        _section_to_interface(section),
    )


def check_fritz_wan_if(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> type_defs.CheckResult:
    params_updated = dict(params)
    params_updated.update({
        'assumed_speed_in': int(section['NewLayer1DownstreamMaxBitRate']),
        'assumed_speed_out': int(section['NewLayer1UpstreamMaxBitRate']),
        'unit': 'bit',
    })
    yield from interfaces.check_multiple_interfaces(
        item,
        params_updated,
        _section_to_interface(section),
    )


register.check_plugin(
    name="fritz_wan_if",
    sections=["fritz"],
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=discover_fritz_wan_if,
    check_ruleset_name="if",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_fritz_wan_if,
)


def discover_fritz_conn(section: Section) -> DiscoveryResult:
    conn_stat = section.get("NewConnectionStatus")
    if conn_stat and conn_stat != "Unconfigured" and "NewExternalIPAddress" in section:
        yield Service()


def check_fritz_conn(section: Section) -> CheckResult:
    conn_stat = section.get("NewConnectionStatus")
    yield Result(
        state=State.OK,
        summary="Status: %s" % conn_stat,
    )

    if conn_stat not in ("Connected", "Connecting", "Disconnected", "Unconfigured"):
        yield Result(
            state=State.UNKNOWN,
            summary="unhandled connection status",
        )

    if conn_stat == "Connected":
        yield Result(
            state=State.OK,
            summary="WAN IP Address: %s" % section.get("NewExternalIPAddress"),
        )
    else:
        yield Result(
            state=State.WARN,
            summary="Not connected",
        )

    last_err = section.get("NewLastConnectionError")
    if last_err and last_err != "ERROR_NONE":
        yield Result(
            state=State.OK,
            summary="Last Error: %s" % last_err,
        )

    uptime_str = section.get("NewUptime")
    if uptime_str:
        yield from uptime.check(
            {},
            uptime.Section(
                uptime_sec=float(uptime_str),
                message=None,
            ),
        )


register.check_plugin(
    name="fritz_conn",
    sections=["fritz"],
    service_name="Connection",
    discovery_function=discover_fritz_conn,
    check_function=check_fritz_conn,
)


def discover_fritz_config(section: Section) -> DiscoveryResult:
    if "NewDNSServer1" in section:
        yield Service()


def check_fritz_config(section: Section) -> CheckResult:
    label_val = [
        ("Auto Disconnect Time", section.get("NewAutoDisconnectTime", "0.0.0.0")),
        ("DNS-Server1", section.get("NewDNSServer1", "0.0.0.0")),
        ("DNS-Server2", section.get("NewDNSServer2", "0.0.0.0")),
        ("VoIP-DNS-Server1", section.get("NewVoipDNSServer1", "0.0.0.0")),
        ("VoIP-DNS-Server2", section.get("NewVoipDNSServer2", "0.0.0.0")),
        ("uPnP Config Enabled", section.get("NewUpnpControlEnabled", "0.0.0.0")),
    ]
    output = ["%s: %s" % (l, v) for l, v in label_val if v != "0.0.0.0"]
    yield (Result(
        state=State.OK,
        summary=", ".join(output),
    ) if output else Result(
        state=State.UNKNOWN,
        summary="Configuration info is missing",
    ))


register.check_plugin(
    name="fritz_config",
    sections=["fritz"],
    service_name="Configuration",
    discovery_function=discover_fritz_config,
    check_function=check_fritz_config,
)


def discover_fritz_link(section: Section) -> DiscoveryResult:
    if "NewLinkStatus" in section and "NewPhysicalLinkStatus" in section:
        yield Service()


def check_fritz_link(section: Section) -> CheckResult:
    label_val = [
        ("Link Status", section.get("NewLinkStatus")),
        ("Physical Link Status", section.get("NewPhysicalLinkStatus")),
        ("Link Type", section.get("NewLinkType")),
        ("WAN Access Type", section.get("NewWANAccessType")),
    ]
    output = ["%s: %s" % (l, v) for l, v in label_val if v]
    yield (Result(
        state=State.OK,
        summary=", ".join(output),
    ) if output else Result(
        state=State.UNKNOWN,
        summary="Link info is missing",
    ))


register.check_plugin(
    name="fritz_link",
    sections=["fritz"],
    service_name="Link Info",
    discovery_function=discover_fritz_link,
    check_function=check_fritz_link,
)
