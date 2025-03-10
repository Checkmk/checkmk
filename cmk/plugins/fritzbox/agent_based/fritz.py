#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    InventoryPlugin,
    InventoryResult,
    Result,
    RuleSetType,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib import interfaces, uptime

Section = Mapping[str, str]


def parse_fritz(string_table: StringTable) -> Section:
    return {line[0]: " ".join(line[1:]) for line in string_table if len(line) > 1}


agent_section_fritz = AgentSection(
    name="fritz",
    parse_function=parse_fritz,
)

_WAN_IF_KEYS = {
    "NewLayer1DownstreamMaxBitRate",
    "NewLinkStatus",
    "NewPhysicalLinkStatus",
    "NewTotalBytesReceived",
    "NewTotalBytesSent",
}

_LINK_STATUS_MAP = {
    None: "4",
    "Up": "1",
}


def _section_to_interface(section: Section) -> interfaces.Section[interfaces.InterfaceWithCounters]:
    if not _WAN_IF_KEYS & set(section):
        return []
    return [
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index="0",
                descr="WAN",
                alias="WAN",
                type="6",
                speed=int(section.get("NewLayer1DownstreamMaxBitRate", 0)),
                oper_status=_LINK_STATUS_MAP.get(
                    section.get("NewLinkStatus") or section.get("NewPhysicalLinkStatus"),
                    "2",
                ),
            ),
            interfaces.Counters(
                in_octets=int(
                    section.get(
                        "NewX_AVM_DE_TotalBytesReceived64", section.get("NewTotalBytesReceived", 0)
                    )
                ),
                out_octets=int(
                    section.get("NewX_AVM_DE_TotalBytesSent64", section.get("NewTotalBytesSent", 0))
                ),
            ),
        )
    ]


def discover_fritz_wan_if(
    params: Sequence[Mapping[str, Any]],
    section: Section,
) -> DiscoveryResult:
    yield from interfaces.discover_interfaces(
        params,
        _section_to_interface(section),
    )


def check_fritz_wan_if(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    yield from interfaces.check_multiple_interfaces(
        item,
        {
            **params,
            **{
                key_params: int(raw_value)
                for (key_params, key_section) in (
                    (
                        "assumed_speed_in",
                        "NewLayer1DownstreamMaxBitRate",
                    ),
                    (
                        "assumed_speed_out",
                        "NewLayer1UpstreamMaxBitRate",
                    ),
                )
                if (raw_value := section.get(key_section))
            },
            "unit": "bit",
        },
        _section_to_interface(section),
    )


check_plugin_fritz_wan_if = CheckPlugin(
    name="fritz_wan_if",
    sections=["fritz"],
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=discover_fritz_wan_if,
    check_ruleset_name="interfaces",
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
    elif conn_stat:
        yield Result(
            state=State.UNKNOWN,
            summary=f"Connection status: {conn_stat}",
        )

    if (last_err := section.get("NewLastConnectionError")) and last_err != "ERROR_NONE":
        yield Result(
            state=State.OK,
            summary="Last Error: %s" % last_err,
        )


check_plugin_fritz_conn = CheckPlugin(
    name="fritz_conn",
    sections=["fritz"],
    service_name="Connection",
    discovery_function=discover_fritz_conn,
    check_function=check_fritz_conn,
)


def discover_fritz_uptime(section: Section) -> DiscoveryResult:
    if "NewUptime" in section:
        yield Service()


def check_fritz_uptime(
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    if uptime_str := section.get("NewUptime"):
        yield from uptime.check(
            params,
            uptime.Section(
                uptime_sec=float(uptime_str),
                message=None,
            ),
        )


check_plugin_fritz_uptime = CheckPlugin(
    name="fritz_uptime",
    sections=["fritz"],
    service_name="Uptime",
    discovery_function=discover_fritz_uptime,
    check_function=check_fritz_uptime,
    check_default_parameters={},
    check_ruleset_name="uptime",
)


def discover_fritz_link(section: Section) -> DiscoveryResult:
    if "NewLinkStatus" in section and "NewPhysicalLinkStatus" in section:
        yield Service()


_LINK_CHECK_FIELDS = [
    ("NewLinkStatus", "Link status"),
    ("NewPhysicalLinkStatus", "Physical link status"),
]


def check_fritz_link(section: Section) -> CheckResult:
    for key, label in _LINK_CHECK_FIELDS:
        if value := section.get(key):
            yield Result(
                state={"Up": State.OK}.get(
                    value,
                    State.CRIT,
                ),
                summary=f"{label}: {value}",
            )


check_plugin_fritz_link = CheckPlugin(
    name="fritz_link",
    sections=["fritz"],
    service_name="Link Info",
    discovery_function=discover_fritz_link,
    check_function=check_fritz_link,
)


_LINK_INV_FIELDS = [
    ("NewLinkType", "link_type"),
    ("NewWANAccessType", "wan_access_type"),
]

_CONFIG_FIELDS = [
    ("NewAutoDisconnectTime", "auto_disconnect_time"),
    ("NewDNSServer1", "dns_server_1"),
    ("NewDNSServer2", "dns_server_2"),
    ("NewVoipDNSServer1", "voip_dns_server_1"),
    ("NewVoipDNSServer2", "voip_dns_server_2"),
    ("NewUpnpControlEnabled", "upnp_config_enabled"),
]


_UNCONFIGURED_VALUE = "0.0.0.0"


def inventory_fritz(section: Section) -> InventoryResult:
    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes={"model": section.get("VersionDevice")},
    )
    yield Attributes(
        path=["software", "os"],
        inventory_attributes={"version": section.get("VersionOS")},
    )
    yield Attributes(
        path=["software", "applications", "fritz"],
        inventory_attributes={
            **{
                inv_key: value
                for section_key, inv_key in _LINK_INV_FIELDS
                if (value := section.get(section_key))
            },
            **{
                inv_key: value
                for section_key, inv_key in _CONFIG_FIELDS
                if (value := section.get(section_key, _UNCONFIGURED_VALUE)) != _UNCONFIGURED_VALUE
            },
        },
    )


inventory_plugin_fritz = InventoryPlugin(
    name="fritz",
    inventory_function=inventory_fritz,
)
