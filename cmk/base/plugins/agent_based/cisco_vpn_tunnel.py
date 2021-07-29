#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, List, Mapping, Tuple

from .agent_based_api.v1 import any_of, contains, OIDEnd, register, SNMPTree, startswith
from .agent_based_api.v1.type_defs import StringTable

VPNTunnel = Dict[str, Tuple[float, float]]
Section = Mapping[str, VPNTunnel]


def parse_cisco_vpn_tunnel(string_table: List[StringTable]) -> Section:
    pre_parsed: Dict[str, Dict[str, float]] = {}
    for index, state, phase_2_in, phase_2_out in string_table[1]:
        if state != "2":
            pre_parsed.setdefault(index, {"in": 0, "out": 0})
            if phase_2_in:
                pre_parsed[index]["in"] += float(phase_2_in)
            if phase_2_out:
                pre_parsed[index]["out"] += float(phase_2_out)

    parsed: Dict[str, VPNTunnel] = {}
    for oid_end, remote_ip, phase_1_in, phase_1_out in string_table[0]:
        parsed.setdefault(remote_ip, {
            "phase_1": (float(phase_1_in), float(phase_1_out)),
        })

        if oid_end in pre_parsed:
            parsed[remote_ip].update({
                "phase_2": (pre_parsed[oid_end]["in"], pre_parsed[oid_end]["out"]),
            })

    return parsed


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
