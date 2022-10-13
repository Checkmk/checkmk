#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

from .agent_based_api.v1 import register
from .utils.threepar import parse_3par

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
        self.name = "%s Node %s Slot %s Port %s" % (
            PROTOCOLS.get(self.protocol),
            self.node,
            self.slot,
            self.cardPort,
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


register.agent_section(
    name="3par_ports",
    parse_function=parse_3par_ports,
)
