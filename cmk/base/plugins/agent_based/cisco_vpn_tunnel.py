#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional

from .agent_based_api.v1 import any_of, contains, OIDEnd, register, SNMPTree, startswith
from .agent_based_api.v1.type_defs import StringTable


@dataclass
class Phase():
    input: float
    output: float


@dataclass
class VPNTunnel:
    phase_1: Phase
    phase_2: Optional[Phase] = None


Section = Mapping[str, VPNTunnel]


def _parse_phase_2(table_phase_2) -> Mapping[str, Phase]:
    phase_2_data: Dict[str, Phase] = {}
    for index, state, phase_2_in, phase_2_out in table_phase_2:
        if state == "2":
            continue
        phase_2 = phase_2_data.setdefault(
            index,
            Phase(0, 0),
        )
        if phase_2_in:
            phase_2.input += float(phase_2_in)
        if phase_2_out:
            phase_2.output += float(phase_2_out)
    return phase_2_data


def parse_cisco_vpn_tunnel(string_table: List[StringTable]) -> Section:
    phase_2_data = _parse_phase_2(string_table[1])

    section: Dict[str, VPNTunnel] = {}
    for oid_end, remote_ip, phase_1_in, phase_1_out in string_table[0]:
        if not remote_ip:
            continue
        tunnel = section.setdefault(
            remote_ip,
            VPNTunnel(Phase(float(phase_1_in), float(phase_1_out))),
        )
        tunnel.phase_2 = phase_2_data.get(
            oid_end,
            tunnel.phase_2,
        )

    return section


register.snmp_section(
    name="cisco_vpn_tunnel",
    parse_function=parse_cisco_vpn_tunnel,
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.1.0", "cisco adaptive security"),
        contains(".1.3.6.1.2.1.1.1.0", "vpn 3000 concentrator"),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.171.1.2.3.1",
            oids=[
                OIDEnd(),
                "7",  # cikeTunRemoteValue
                "19",  # cikeTunInOctets,  phase 1 (handshake)
                "27",  # cikeTunOutOctets, phase 1 (handshake)
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.171.1.3.2.1",
            oids=[
                "2",  # cipSecTunIkeTunnelIndex
                "3",  # cipSecTunIkeTunnelAlive
                "26",  # cipSecTunInOctets,  phase 2 (throughput)
                "39",  # cipSecTunOutOctets, phase 2 (throughput)
            ],
        )
    ],
)
