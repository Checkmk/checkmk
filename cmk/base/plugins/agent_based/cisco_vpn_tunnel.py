#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from time import time
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple, TypedDict

from .agent_based_api.v1 import (
    any_of,
    contains,
    get_rate,
    get_value_store,
    GetRateError,
    IgnoreResultsError,
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
class Phase:
    input: float
    output: float

    def rates(
        self,
        value_store: MutableMapping[str, Any],
        value_store_key_prefix: str,
        now: float,
    ) -> Optional["Phase"]:
        try:
            rate_input: Optional[float] = get_rate(
                value_store,
                f"{value_store_key_prefix}_input",
                now,
                self.input,
                raise_overflow=True,
            )
        except GetRateError:
            rate_input = None
        try:
            rate_output: Optional[float] = get_rate(
                value_store,
                f"{value_store_key_prefix}_output",
                now,
                self.output,
                raise_overflow=True,
            )
        except GetRateError:
            rate_output = None
        return (
            None
            if rate_input is None or rate_output is None
            else Phase(
                rate_input,
                rate_output,
            )
        )


@dataclass
class VPNTunnel:
    phase_1: Phase
    phase_2: Optional[Phase] = None

    def rates(
        self,
        value_store: MutableMapping[str, Any],
        now: float,
    ) -> "VPNTunnel":
        rates_phase_1 = self.phase_1.rates(
            value_store,
            "phase_1",
            now,
        )
        if self.phase_2:
            rates_phase_2 = self.phase_2.rates(
                value_store,
                "phase_2",
                now,
            )
        else:
            rates_phase_2 = None
        if rates_phase_1 is None or (self.phase_2 and rates_phase_2 is None):
            raise IgnoreResultsError("Initializing counters")
        return VPNTunnel(
            rates_phase_1,
            rates_phase_2,
        )


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
        ),
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
    revelant_tunnel_settings = [
        (
            alias,
            state_missing,
        )
        for ip, alias, state_missing in params.get("tunnels", [])
        if ip == item
    ]
    return (
        State(
            revelant_tunnel_settings[-1][1]
            if revelant_tunnel_settings
            else params.get(
                "state",
                2,
            )
        ),
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

    if not (vpn_tunnel := section.get(item)):
        yield Result(
            state=state_missing,
            summary="%sTunnel is missing" % (aliases + " " if aliases else ""),
        )
        return

    rates = vpn_tunnel.rates(
        get_value_store(),
        time(),
    )

    yield Result(
        state=State.OK,
        summary="%sPhase 1: in: %s, out: %s"
        % (
            aliases + " " if aliases else "",
            networkbandwidth(rates.phase_1.input),
            networkbandwidth(rates.phase_1.output),
        ),
    )

    if rates.phase_2:
        yield Result(
            state=State.OK,
            summary="Phase 2: in: %s, out: %s"
            % (
                networkbandwidth(rates.phase_2.input),
                networkbandwidth(rates.phase_2.output),
            ),
        )

    else:
        yield Result(
            state=State.OK,
            summary="Phase 2 missing",
        )

    yield Metric(
        name="if_in_octets",
        value=rates.phase_1.input + (rates.phase_2.input if rates.phase_2 else 0),
    )
    yield Metric(
        name="if_out_octets",
        value=rates.phase_1.output + (rates.phase_2.output if rates.phase_2 else 0),
    )


register.check_plugin(
    name="cisco_vpn_tunnel",
    service_name="VPN Tunnel %s",
    discovery_function=discover_cisco_vpn_tunnel,
    check_function=check_cisco_vpn_tunnel,
    check_default_parameters={},
    check_ruleset_name="vpn_tunnel",
)
