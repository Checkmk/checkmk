#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from time import time
from typing import Dict, List, Mapping, Optional, Sequence, Tuple, TypedDict

from .agent_based_api.v1 import (
    any_of,
    contains,
    get_rate,
    get_value_store,
    GetRateError,
    IgnoreResults,
    Metric,
    OIDEnd,
    register,
    Result,
    Service,
    SNMPTree,
    startswith,
    State,
)
from .agent_based_api.v1.render import networkbandwidth
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


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


class CheckParameters(
        TypedDict,
        total=False,
):
    state: int
    tunnels: Sequence[Tuple[str, str, int]]


def discover_cisco_vpn_tunnel(section: Section) -> DiscoveryResult:
    yield from (Service(item=ip) for ip in section)


def _state_missing_and_aliases(
    item: str,
    params: CheckParameters,
) -> Tuple[State, str]:
    revelant_tunnel_settings = [(
        alias,
        state_missing,
    ) for ip, alias, state_missing in params.get("tunnels", []) if ip == item]
    return (
        State(revelant_tunnel_settings[-1][1] if revelant_tunnel_settings else params.get(
            "state",
            2,
        )),
        " ".join(f"[{alias}]" for alias, _state_missing in revelant_tunnel_settings),
    )


def check_cisco_vpn_tunnel(
    item: str,
    params: CheckParameters,
    section: Section,
) -> CheckResult:

    state_missing, aliases = _state_missing_and_aliases(
        item,
        params,
    )

    if item in section:
        now = time()
        value_store = get_value_store()
        vpn_tunnel = section[item]
        try:
            phase1_in_rate = get_rate(
                value_store,
                "cisco_vpn_tunnel_phase_1_in.%s" % item,
                now,
                vpn_tunnel.phase_1.input,
                raise_overflow=True,
            )
        except GetRateError:
            phase1_in_rate = 0
            yield IgnoreResults("Initialzing counters")
        try:
            phase1_out_rate = get_rate(
                value_store,
                "cisco_vpn_tunnel_phase_1_out.%s" % item,
                now,
                vpn_tunnel.phase_1.output,
                raise_overflow=True,
            )
        except GetRateError:
            phase1_out_rate = 0
            yield IgnoreResults("Initialzing counters")
        yield Result(
            state=State.OK,
            summary="%sPhase 1: in: %s, out: %s" % (
                aliases + " " if aliases else "",
                networkbandwidth(phase1_in_rate),
                networkbandwidth(phase1_out_rate),
            ),
        )

        if vpn_tunnel.phase_2:
            try:
                phase2_in_rate = get_rate(
                    value_store,
                    "cisco_vpn_tunnel_phase_2_in.%s" % item,
                    now,
                    vpn_tunnel.phase_2.input,
                    raise_overflow=True,
                )
            except GetRateError:
                phase2_in_rate = 0
                yield IgnoreResults("Initialzing counters")
            try:
                phase2_out_rate = get_rate(
                    value_store,
                    "cisco_vpn_tunnel_phase_2_out.%s" % item,
                    now,
                    vpn_tunnel.phase_2.output,
                    raise_overflow=True,
                )
            except GetRateError:
                phase2_out_rate = 0
                yield IgnoreResults("Initialzing counters")
            yield Result(
                state=State.OK,
                summary="Phase 2: in: %s, out: %s" % (
                    networkbandwidth(phase2_in_rate),
                    networkbandwidth(phase2_out_rate),
                ),
            )

        else:
            phase2_in_rate, phase2_out_rate = 0, 0
            yield Result(
                state=State.OK,
                summary="Phase 2 missing",
            )

        in_rate = phase1_in_rate + phase2_in_rate
        out_rate = phase1_out_rate + phase2_out_rate

    else:
        yield Result(
            state=state_missing,
            summary="%sTunnel is missing" % (aliases + " " if aliases else ""),
        )
        in_rate = out_rate = 0

    yield Metric(
        name="if_in_octets",
        value=in_rate,
    )
    yield Metric(
        name="if_out_octets",
        value=out_rate,
    )


register.check_plugin(
    name="cisco_vpn_tunnel",
    service_name="VPN Tunnel %s",
    discovery_function=discover_cisco_vpn_tunnel,
    check_function=check_cisco_vpn_tunnel,
    check_default_parameters={},
    check_ruleset_name="vpn_tunnel",
)
