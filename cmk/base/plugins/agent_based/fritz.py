#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence

from .agent_based_api.v1 import Attributes, register, Result, Service, State, type_defs
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils import interfaces, uptime

Section = Mapping[str, str]


def parse_fritz(string_table: type_defs.StringTable) -> Section:
    return {line[0]: " ".join(line[1:]) for line in string_table if len(line) > 1}


register.agent_section(
    name="fritz",
    parse_function=parse_fritz,
)


_LINK_STATUS_MAP = {
    None: "4",
    "Up": "1",
}


def _section_to_interface(section: Section) -> interfaces.Section:
    return [
        interfaces.Interface(
            index="0",
            descr="WAN",
            alias="WAN",
            type="6",
            speed=int(section.get("NewLayer1DownstreamMaxBitRate", 0)),
            oper_status=_LINK_STATUS_MAP.get(
                section.get("NewLinkStatus"),
                "2",
            ),
            in_octets=int(section.get("NewTotalBytesReceived", 0)),
            out_octets=int(section.get("NewTotalBytesSent", 0)),
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
    params_updated.update(
        {
            "assumed_speed_in": int(section["NewLayer1DownstreamMaxBitRate"]),
            "assumed_speed_out": int(section["NewLayer1UpstreamMaxBitRate"]),
            "unit": "bit",
        }
    )
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
    if (
        (conn_stat := section.get("NewConnectionStatus"))
        and conn_stat != "Unconfigured"
        and "NewExternalIPAddress" in section
    ):
        yield Service()


def check_fritz_conn(section: Section) -> CheckResult:
    if (conn_stat := section.get("NewConnectionStatus")) == "Connected":
        yield Result(
            state=State.OK,
            summary=f"Connection status: {conn_stat}",
        )
        yield Result(
            state=State.OK,
            summary=f"WAN IP Address: {section.get('NewExternalIPAddress', 'unknown')}",
        )
    elif conn_stat in {
        "Connected",
        "Connecting",
        "Disconnected",
        "Unconfigured",
    }:
        yield Result(
            state=State.WARN,
            summary=f"Connection status: {conn_stat}",
        )
    else:
        yield Result(
            state=State.UNKNOWN,
            summary=f"Connection status: {conn_stat}"
            if conn_stat
            else "Got no connection status from device",
        )

    if (last_err := section.get("NewLastConnectionError")) and last_err != "ERROR_NONE":
        yield Result(
            state=State.OK,
            summary="Last Error: %s" % last_err,
        )

    if uptime_str := section.get("NewUptime"):
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


_CONFIG_FIELDS = [
    ("NewAutoDisconnectTime", "Auto-disconnect time"),
    ("NewDNSServer1", "DNS server 1"),
    ("NewDNSServer2", "DNS server 2"),
    ("NewVoipDNSServer1", "VoIP DNS server 1"),
    ("NewVoipDNSServer2", "VoIP DNS server 2"),
    ("NewUpnpControlEnabled", "uPnP config enabled"),
]

_UNCONFIGURED_VALUE = "0.0.0.0"


def check_fritz_config(section: Section) -> CheckResult:
    output = [
        f"{label}: {value}"
        for key, label in _CONFIG_FIELDS
        if (
            value := section.get(
                key,
                _UNCONFIGURED_VALUE,
            )
        )
        != _UNCONFIGURED_VALUE
    ]
    yield (
        Result(
            state=State.OK,
            summary=", ".join(output),
        )
        if output
        else Result(
            state=State.UNKNOWN,
            summary="Configuration info is missing",
        )
    )


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


_LINK_FIELDS = [
    ("NewLinkStatus", "Link status"),
    ("NewPhysicalLinkStatus", "Physical link status"),
    ("NewLinkType", "Link type"),
    ("NewWANAccessType", "WAN access type"),
]


def check_fritz_link(section: Section) -> CheckResult:
    output = [f"{label}: {value}" for key, label in _LINK_FIELDS if (value := section.get(key))]
    yield (
        Result(
            state=State.OK,
            summary=", ".join(output),
        )
        if output
        else Result(
            state=State.UNKNOWN,
            summary="Link info is missing",
        )
    )


register.check_plugin(
    name="fritz_link",
    sections=["fritz"],
    service_name="Link Info",
    discovery_function=discover_fritz_link,
    check_function=check_fritz_link,
)


def inventory_fritz(section: Section) -> type_defs.InventoryResult:
    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes={"model": section.get("VersionDevice")},
    )
    yield Attributes(
        path=["software", "os"],
        inventory_attributes={"version": section.get("VersionOS")},
    )


register.inventory_plugin(
    name="fritz",
    inventory_function=inventory_fritz,
)
