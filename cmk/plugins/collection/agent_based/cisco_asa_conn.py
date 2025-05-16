#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


@dataclass()
class NetworkInterfaceData:
    if_name: str | None = None
    admin_status: str | None = None
    oper_status: str | None = None
    ip_address: str | None = None


Section = dict[str, NetworkInterfaceData]


def parse_cisco_asa_conn(string_table: Sequence[StringTable]) -> Section:
    network_interfaces: Section = {}

    for line in string_table[0]:
        network_interfaces[line[0]] = NetworkInterfaceData(if_name=line[1])

    for line in string_table[2]:
        network_interfaces[line[0]].admin_status = line[1]
        network_interfaces[line[0]].oper_status = line[2]

    for line in string_table[1]:
        if line[0] not in network_interfaces:
            # this is an IP but without network interface
            network_interfaces[line[0]] = NetworkInterfaceData(admin_status="1")
        network_interfaces[line[0]].ip_address = line[1]

    return network_interfaces


def inventory_cisco_asa_conn(section: Section) -> DiscoveryResult:
    for if_index, if_data in section.items():
        if if_data.admin_status == "1" and if_data.ip_address is not None:
            yield Service(item=if_index)


def check_cisco_asa_conn(item: str, section: Section) -> CheckResult:
    translate_oper_status = {
        "1": (State.OK, "up"),
        "2": (State.CRIT, "down"),
        "3": (State.UNKNOWN, "testing"),
        "4": (State.UNKNOWN, "unknown"),
        "5": (State.CRIT, "dormant"),
        "6": (State.CRIT, "not present"),
        "7": (State.CRIT, "lower layer down"),
    }

    if_data = section.get(item)
    if if_data is None:
        return

    if if_data.if_name:
        yield Result(state=State.OK, summary=f"Name: {if_data.if_name}")

    if if_data.ip_address:
        if if_data.if_name:
            yield Result(state=State.OK, summary=f"IP: {if_data.ip_address}")
        else:
            yield Result(
                state=State.UNKNOWN,
                summary=f"IP: {if_data.ip_address} - No network device associated",
            )
    else:  # CRIT if no IP is assigned
        yield Result(state=State.CRIT, summary="IP: Not found!")

    if if_data.oper_status:
        state, state_readable = translate_oper_status.get(
            if_data.oper_status, (State.UNKNOWN, "N/A")
        )
        yield Result(state=state, summary=f"Status: {state_readable}")


snmp_section_cisco_asa_conn = SNMPSection(
    name="cisco_asa_conn",
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.1.0", "cisco adaptive security"),
        startswith(".1.3.6.1.2.1.1.1.0", "cisco firewall services"),
        contains(".1.3.6.1.2.1.1.1.0", "cisco pix security"),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.31.1.1.1",
            oids=[
                OIDEnd(),  # IP-MIB::ipAdEntIfIndex
                "1",  # IF-MIB::ifName
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.4.20.1",
            oids=[
                "2",  # IP-MIB::ipAdEntIfIndex
                "1",  # IP-MIB::ipAdEntAddr
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.2.2.1",
            oids=[
                OIDEnd(),  # IP-MIB::ipAdEntIfIndex
                "7",  # IF-MIB::ifAdminStatus
                "8",  # IF-MIB::ifOperStatus
            ],
        ),
    ],
    parse_function=parse_cisco_asa_conn,
)


check_plugin_cisco_asa_conn = CheckPlugin(
    name="cisco_asa_conn",
    service_name="Connection %s",
    discovery_function=inventory_cisco_asa_conn,
    check_function=check_cisco_asa_conn,
)
