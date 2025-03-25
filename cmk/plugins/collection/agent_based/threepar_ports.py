#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field

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
from cmk.plugins.lib.threepar import parse_3par

THREEPAR_PORTS_DEFAULT_LEVELS = {
    "1_link": 1,
    "2_link": 1,
    "3_link": 1,
    "4_link": 0,
    "5_link": 2,
    "6_link": 2,
    "7_link": 1,
    "8_link": 0,
    "9_link": 1,
    "10_link": 1,
    "11_link": 1,
    "12_link": 1,
    "13_link": 1,
    "14_link": 1,
    "1_fail": 0,
    "2_fail": 2,
    "3_fail": 2,
    "4_fail": 2,
    "5_fail": 2,
    "6_fail": 2,
    "7_fail": 1,
}
PROTOCOLS = {
    1: "FC",
    2: "iSCSI",
    3: "FCOE",
    4: "IP",
    5: "SAS",
    6: "NVMe",
}

FAILOVERS = {
    1: "NONE",
    2: "FAILOVER_PENDING",
    3: "FAILED_OVER",
    4: "ACTIVE",
    5: "ACTIVE_DOWN",
    6: "ACTIVE_FAILED",
    7: "FAILBACK_PENDING",
}

LINKS = {
    1: "CONFIG_WAIT",
    2: "ALPA_WAIT",
    3: "LOGIN_WAIT",
    4: "READY",
    5: "LOSS_SYNC",
    6: "ERROR_STATE",
    7: "XXX",
    8: "NONPARTICIPATE",
    9: "COREDUMP",
    10: "OFFLINE",
    11: "FWDEAD",
    12: "IDLE_FOR_RESET",
    13: "DHCP_IN_PROGRESS",
    14: "PENDING_RESET",
}

MODES = {
    1: "SUSPENDED",
    2: "TARGET",
    3: "INITIATOR",
    4: "PEER",
}


@dataclass
class ThreeParPort:
    label: str | None
    type: int
    state: int | None
    translated_state: str | None
    protocol: int
    portWWN: str | None
    mode: int | None
    translated_mode: str | None
    failoverState: int | None
    translated_failover: str | None
    name: str = field(init=False)
    node: int
    slot: int
    cardPort: int

    def __post_init__(self):
        self.name = (
            f"{PROTOCOLS.get(self.protocol)} Node {self.node} Slot {self.slot} Port {self.cardPort}"
        )


ThreeParPortsSection = Mapping[str, ThreeParPort]


def parse_3par_ports(string_table: StringTable) -> ThreeParPortsSection:
    threepar_ports: MutableMapping[str, ThreeParPort] = {}

    for port in parse_3par(string_table).get("members", {}):
        if PROTOCOLS.get(port["protocol"]) is None:
            continue

        port_state = port.get("linkState")
        port_mode = port.get("mode")
        port_failoverState = port.get("failoverState")

        port = ThreeParPort(
            label=port.get("label"),
            type=port["type"],
            state=port_state,
            translated_state=LINKS.get(port_state),
            protocol=port["protocol"],
            node=port["portPos"]["node"],
            slot=port["portPos"]["slot"],
            cardPort=port["portPos"]["cardPort"],
            portWWN=port.get("portWWN"),
            mode=port_mode,
            translated_mode=MODES.get(port_mode),
            failoverState=port_failoverState,
            translated_failover=FAILOVERS.get(port_failoverState),
        )
        threepar_ports.setdefault(port.name, port)

    return threepar_ports


agent_section_3par_ports = AgentSection(
    name="3par_ports",
    parse_function=parse_3par_ports,
)


def discover_3par_ports(section: ThreeParPortsSection) -> DiscoveryResult:
    for port in section.values():
        # Only create an item if not "FREE" (type = 3)
        if port.type != 3:
            yield Service(item=port.name)


def check_3par_ports(
    item: str,
    params: Mapping[str, int],
    section: ThreeParPortsSection,
) -> CheckResult:
    if (port := section.get(item)) is None:
        return

    if port.label:
        yield Result(state=State.OK, summary=f"Label: {port.label}")

    if port.state and port.translated_state:
        yield Result(
            state=State(params.get(f"{port.state}_link")),
            summary=port.translated_state,
        )

    if port.portWWN:
        yield Result(state=State.OK, summary=f"portWWN: {port.portWWN}")

    if port.mode:
        yield Result(
            state=State.OK,
            summary=f"Mode: {port.translated_mode}",
        )

    if port.failoverState:
        yield Result(
            state=State(params.get(f"{port.failoverState}_fail")),
            summary=f"Failover: {port.translated_failover}",
        )


check_plugin_3par_ports = CheckPlugin(
    name="3par_ports",
    service_name="Port %s",
    check_function=check_3par_ports,
    check_default_parameters=THREEPAR_PORTS_DEFAULT_LEVELS,
    check_ruleset_name="threepar_ports",
    discovery_function=discover_3par_ports,
)
