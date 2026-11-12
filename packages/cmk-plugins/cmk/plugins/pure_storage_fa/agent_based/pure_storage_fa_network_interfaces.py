#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Optional
from pydantic import BaseModel

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
    Metric,
)


class Name(BaseModel, frozen=True):
    name: Optional[str] = None


class Eth(BaseModel, frozen=True):
    address: Optional[str] = None
    mac_address: Optional[str] = None
    gateway: Optional[str] = None
    vlan: Optional[int] = None
    mtu: Optional[int] = None
    netmask: Optional[str] = None
    subinterfaces: Optional[list] = None
    subtype: Optional[str] = None
    subnet: Optional[Name] = None


class Interface(BaseModel, frozen=True):
    name: Optional[str] = None
    services: Optional[list] = None
    enabled: Optional[bool] = None
    interface_type: Optional[str] = None
    speed: Optional[int] = None
    attached_servers: Optional[list] = None
    eth: Optional[Eth] = None
    services: Optional[list] = None


def parse_network_interfaces(string_table: StringTable) -> list[Interface] | None:
    json_data = json.loads(string_table[0][0])
    if "items" not in json_data:
        return None
    parsed = []
    for interface in json_data["items"]:
        parsed.append(Interface(**interface))

    return parsed


agent_section_pure_storage_fa_network_interfaces = AgentSection(
    name="pure_storage_fa_network_interfaces",
    parse_function=parse_network_interfaces,
)


def discover_network_interfaces(section: list[Interface]) -> DiscoveryResult:
    for interface in section:
        params = {
            "discovered_state": [interface.enabled, "True"],
            "discovered_speed": interface.speed,
        }
        yield Service(item=interface.name, parameters=dict(params))


def check_network_interfaces(item, params, section: list[Interface]) -> CheckResult:
    if section == []:
        yield Result(state=State.CRIT, summary="No Network Interfaces found")

    for interface in section:
        if item == interface.name:
            details = ""
            if (
                interface.enabled in params["discovered_state"]
                and interface.speed >= params["discovered_speed"]
            ):
                if interface.enabled:
                    state = State.OK
                    summary = f"Interface {interface.name} running with IP {interface.eth.address}, MAC {interface.eth.mac_address} and {int(interface.speed) / 1000000000} Gbps."
                    details = f"Gateway: {interface.eth.gateway}\nNetmask: {interface.eth.netmask}\nMTU: {interface.eth.mtu}\nSubnet: {interface.eth.subnet.name}"
                else:
                    state = State.OK
                    summary = f"Interface {interface.name} is currently not running"
                    details = f"MAC: {interface.eth.mac_address}\nMTU: {interface.eth.mtu}\nSpeed: {int(interface.speed) / 1000000000} Gbps."
            elif (
                interface.enabled in params["discovered_state"]
                and interface.speed < params["discovered_speed"]
            ):
                if interface.enabled:
                    state = State.WARN
                    summary = f"Interface {interface.name} running with only {int(interface.speed) / 1000000000} Gbps."
                    details = f"Normal Speed: {params['discovered_speed']}\nIP: {interface.eth.address}\nMAC: {interface.eth.mac_address}\nGateway: {interface.eth.gateway}\nNetmask: {interface.eth.netmask}\nMTU: {interface.eth.mtu}\nSubnet: {interface.eth.subnet.name}"
                else:
                    state = State.WARN
                    summary = f"Interface {interface.name} is currently not running, but check speed please"
                    details = f"Speed: {int(interface.speed) / 1000000000}\nNormal Speed: {params['discovered_speed']}\nIP: {interface.eth.address}\nMAC: {interface.eth.mac_address}\nGateway: {interface.eth.gateway}\nNetmask: {interface.eth.netmask}\nMTU: {interface.eth.mtu}\nSubnet: {interface.eth.subnet.name}"
            else:
                state = State.CRIT
                summary = f"Interface {interface.name} is down"
                details = f"Speed: {int(interface.speed) / 1000000000}\nNormal Speed: {params['discovered_speed']}\nIP: {interface.eth.address}\nMAC: {interface.eth.mac_address}Gateway: {interface.eth.gateway}\nNetmask: {interface.eth.netmask}\nMTU: {interface.eth.mtu}\nSubnet: {interface.eth.subnet.name}"

            yield Metric("pure_storage_fa_network_interfaces_speed", int(interface.speed) / 1000000000)
            yield Result(state=state, summary=summary, details=details)


check_plugin_pure_storage_fa_network_interfaces = CheckPlugin(
    name="pure_storage_fa_network_interfaces",
    service_name="Interface %s",
    discovery_function=discover_network_interfaces,
    check_function=check_network_interfaces,
    check_default_parameters={},
)
