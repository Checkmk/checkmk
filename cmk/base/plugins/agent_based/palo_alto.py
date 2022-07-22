#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from dataclasses import dataclass
from typing import Mapping

from .agent_based_api.v1 import contains, register, Result, Service, SNMPTree, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


@dataclass(frozen=True)
class SectionPaloAlto:
    firmware_version: str
    ha_local_state: str
    ha_peer_state: str
    ha_mode: str


def parse(string_table: StringTable) -> SectionPaloAlto | None:
    return SectionPaloAlto(*string_table[0]) if string_table else None


register.snmp_section(
    name="palo_alto",
    parse_function=parse,
    detect=contains(".1.3.6.1.2.1.1.2.0", "25461"),
    fetch=SNMPTree(
        ".1.3.6.1.4.1.25461.2.1.2.1",
        [
            "1",  # panSysSwVersion
            "11",  # panSysHAState
            "12",  # panSysHAPeerState
            "13",  # panSysHAMode
        ],
    ),
)


def discover(section: SectionPaloAlto) -> DiscoveryResult:
    yield Service()


_STATE_MAPPING_DEFAULT: Mapping[str, State] = {
    "mode_disabled": State.OK,
    "mode_active_active": State.OK,
    "mode_active_passive": State.OK,
    "ha_local_state_active": State.OK,
    "ha_local_state_passive": State.OK,
    "ha_local_state_active_primary": State.OK,
    "ha_local_state_active_secondary": State.OK,
    "ha_local_state_disabled": State.OK,
    "ha_local_state_tentative": State.WARN,
    "ha_local_state_non_functional": State.CRIT,
    "ha_local_state_suspended": State.CRIT,
    "ha_local_state_unknown": State.UNKNOWN,
    "ha_peer_state_active": State.OK,
    "ha_peer_state_passive": State.OK,
    "ha_peer_state_active_primary": State.OK,
    "ha_peer_state_active_secondary": State.OK,
    "ha_peer_state_disabled": State.OK,
    "ha_peer_state_tentative": State.WARN,
    "ha_peer_state_non_functional": State.CRIT,
    "ha_peer_state_suspended": State.CRIT,
    "ha_peer_state_unknown": State.UNKNOWN,
}


def _uniform_format(name: str) -> str:
    return name.lower().replace("-", "_")


def check(
    params: Mapping[str, State],
    section: SectionPaloAlto,
) -> CheckResult:

    yield Result(state=State.OK, notice=f"Firmware Version: {section.firmware_version}")
    yield Result(
        state=params[f"mode_{_uniform_format(section.ha_mode)}"],
        summary=f"HA mode: {section.ha_mode}",
    )
    yield Result(
        state=params[f"ha_local_state_{_uniform_format(section.ha_local_state)}"],
        summary=f"HA local state: {section.ha_local_state}",
    )
    yield Result(
        state=params[f"ha_peer_state_{_uniform_format(section.ha_peer_state)}"],
        notice=f"HA peer state: {section.ha_peer_state}",
    )


register.check_plugin(
    name="palo_alto",
    service_name="Palo Alto State",
    discovery_function=discover,
    check_function=check,
    check_default_parameters=_STATE_MAPPING_DEFAULT,
)
