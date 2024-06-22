#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.palo_alto import DETECT_PALO_ALTO


@dataclass(frozen=True)
class SectionPaloAlto:
    firmware_version: str
    ha_local_state: str
    ha_peer_state: str
    ha_mode: str


def parse(string_table: StringTable) -> SectionPaloAlto | None:
    return SectionPaloAlto(*string_table[0]) if string_table else None


snmp_section_palo_alto = SimpleSNMPSection(
    name="palo_alto",
    parse_function=parse,
    detect=DETECT_PALO_ALTO,
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


_STATE_MAPPING_DEFAULT: Mapping[str, int] = {
    "mode_disabled": int(State.OK),
    "mode_active_active": int(State.OK),
    "mode_active_passive": int(State.OK),
    "ha_local_state_active": int(State.OK),
    "ha_local_state_passive": int(State.OK),
    "ha_local_state_active_primary": int(State.OK),
    "ha_local_state_active_secondary": int(State.OK),
    "ha_local_state_disabled": int(State.OK),
    "ha_local_state_tentative": int(State.WARN),
    "ha_local_state_non_functional": int(State.CRIT),
    "ha_local_state_suspended": int(State.CRIT),
    "ha_local_state_unknown": int(State.UNKNOWN),
    "ha_peer_state_active": int(State.OK),
    "ha_peer_state_passive": int(State.OK),
    "ha_peer_state_active_primary": int(State.OK),
    "ha_peer_state_active_secondary": int(State.OK),
    "ha_peer_state_disabled": int(State.OK),
    "ha_peer_state_tentative": int(State.WARN),
    "ha_peer_state_non_functional": int(State.CRIT),
    "ha_peer_state_suspended": int(State.CRIT),
    "ha_peer_state_unknown": int(State.UNKNOWN),
}


def _uniform_format(name: str) -> str:
    return name.lower().replace("-", "_")


def check(
    params: Mapping[str, int],
    section: SectionPaloAlto,
) -> CheckResult:
    yield Result(state=State.OK, summary=f"Firmware Version: {section.firmware_version}")
    yield Result(
        state=State(params[f"mode_{_uniform_format(section.ha_mode)}"]),
        summary=f"HA mode: {section.ha_mode}",
    )
    yield Result(
        state=(
            State.OK
            if section.ha_mode == "disabled"
            else State(params[f"ha_local_state_{_uniform_format(section.ha_local_state)}"])
        ),
        summary=f"HA local state: {section.ha_local_state}",
    )
    yield Result(
        state=(
            State.OK
            if section.ha_mode == "disabled"
            else State(params[f"ha_peer_state_{_uniform_format(section.ha_peer_state)}"])
        ),
        notice=f"HA peer state: {section.ha_peer_state}",
    )


check_plugin_palo_alto = CheckPlugin(
    name="palo_alto",
    service_name="Palo Alto State",
    discovery_function=discover,
    check_function=check,
    check_default_parameters=_STATE_MAPPING_DEFAULT,
    check_ruleset_name="palo_alto",
)
