#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.ibm_svc.lib import parse_ibm_svc_with_header

# Example agent output:
# <<<ibm_svc_portsas:sep(58)>>>
# 0:1:6Gb:1:node1:500507680305D3C0:online::host:host_controller:0:1
# 1:2:6Gb:1:node1:500507680309D3C0:online::host:host_controller:0:2
# 2:3:6Gb:1:node1:50050768030DD3C0:online::host:host_controller:0:3
# 3:4:6Gb:1:node1:500507680311D3C0:offline:500507680474F03F:none:enclosure:0:4
# 4:5:N/A:1:node1:500507680315D3C0:offline_unconfigured::none:host_controller:1:1
# 5:6:N/A:1:node1:500507680319D3C0:offline_unconfigured::none:host_controller:1:2
# 6:7:N/A:1:node1:50050768031DD3C0:offline_unconfigured::none:host_controller:1:3
# 7:8:N/A:1:node1:500507680321D3C0:offline_unconfigured::none:host_controller:1:4
# 8:1:6Gb:2:node2:500507680305D3C1:online::host:host_controller:0:1
# 9:2:6Gb:2:node2:500507680309D3C1:online::host:host_controller:0:2
# 10:3:6Gb:2:node2:50050768030DD3C1:online::host:host_controller:0:3
# 11:4:6Gb:2:node2:500507680311D3C1:offline:500507680474F07F:none:enclosure:0:4
# 12:5:N/A:2:node2:500507680315D3C1:offline_unconfigured::none:host_controller:1:1
# 13:6:N/A:2:node2:500507680319D3C1:offline_unconfigured::none:host_controller:1:2
# 14:7:N/A:2:node2:50050768031DD3C1:offline_unconfigured::none:host_controller:1:3
# 15:8:N/A:2:node2:500507680321D3C1:offline_unconfigured::none:host_controller:1:4

# the corresponding header line
# id:port_id:port_speed:node_id:node_name:WWPN:status:switch_WWPN:attachment:type:adapter_location:adapter_port_id


@dataclass(frozen=True)
class SasPort:
    status: str
    port_speed: str
    port_type: str


Section = Mapping[str, SasPort]


class IbmSvcPortsasParams(TypedDict):
    current_state: str


def parse_ibm_svc_portsas(string_table: StringTable) -> Section:
    dflt_header = [
        "id",
        "port_id",
        "port_speed",
        "node_id",
        "node_name",
        "WWPN",
        "status",
        "switch_WWPN",
        "attachment",
        "type",
        "adapter_location",
        "adapter_port_id",
    ]
    parsed: dict[str, SasPort] = {}
    for id_, rows in parse_ibm_svc_with_header(string_table, dflt_header).items():
        try:
            data = rows[0]
        except IndexError:
            continue
        if "node_id" in data and "adapter_location" in data and "adapter_port_id" in data:
            item_name = f"Node {data['node_id']} Slot {data['adapter_location']} Port {data['adapter_port_id']}"
        else:
            item_name = f"Port {id_}"
        parsed.setdefault(
            item_name,
            SasPort(status=data["status"], port_speed=data["port_speed"], port_type=data["type"]),
        )
    return parsed


def discover_ibm_svc_portsas(section: Section) -> DiscoveryResult:
    for item_name, port in section.items():
        if port.status == "offline_unconfigured":
            continue
        yield Service(item=item_name, parameters={"current_state": port.status})


def check_ibm_svc_portsas(item: str, params: IbmSvcPortsasParams, section: Section) -> CheckResult:
    if (port := section.get(item)) is None:
        return

    state = State.OK if port.status == params["current_state"] else State.CRIT
    yield Result(
        state=state,
        summary=f"Status: {port.status}, Speed: {port.port_speed}, Type: {port.port_type}",
    )


agent_section_ibm_svc_portsas = AgentSection(
    name="ibm_svc_portsas",
    parse_function=parse_ibm_svc_portsas,
)


check_plugin_ibm_svc_portsas = CheckPlugin(
    name="ibm_svc_portsas",
    service_name="SAS %s",
    discovery_function=discover_ibm_svc_portsas,
    check_function=check_ibm_svc_portsas,
    check_default_parameters={
        "current_state": "offline",
    },
)
