#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

from .lib import data_by_item, DETECT_AUDIOCODES


@dataclass(frozen=True, kw_only=True)
class OPState:
    name: str
    state: State


@dataclass(frozen=True, kw_only=True)
class Presence:
    name: str
    state: State


@dataclass(frozen=True, kw_only=True)
class HAStatus:
    name: str
    state: State


OPERATIONAL_STATE_MAPPING = {
    "0": OPState(name="Invalid state", state=State.CRIT),
    "1": OPState(name="Disabled", state=State.CRIT),
    "2": OPState(name="Enabled", state=State.OK),
}
PRESENCE_MAPPING = {
    "0": Presence(name="Invalid status", state=State.CRIT),
    "1": Presence(name="Module present", state=State.OK),
    "2": Presence(name="Module missing", state=State.CRIT),
}

HA_STATUS_MAPPING = {
    "0": HAStatus(name="Invalid status", state=State.CRIT),
    "1": HAStatus(name="Active - no HA", state=State.WARN),
    "2": HAStatus(name="Active", state=State.OK),
    "3": HAStatus(name="Redundant", state=State.OK),
    "4": HAStatus(name="Stand alone", state=State.OK),
    "5": HAStatus(name="Redundant - no HA", state=State.WARN),
    "6": HAStatus(name="Not applicable", state=State.UNKNOWN),
}


@dataclass(frozen=True, kw_only=True)
class Module:
    op_state: OPState
    presence: Presence
    ha_status: HAStatus


def parse_audiocodes_operational_state(string_table: StringTable) -> Mapping[str, Module] | None:
    if not string_table:
        return None

    return {
        module[0]: Module(
            op_state=OPERATIONAL_STATE_MAPPING[module[1]],
            presence=PRESENCE_MAPPING[module[2]],
            ha_status=HA_STATUS_MAPPING[module[3]],
        )
        for module in string_table
    }


snmp_section_audiocodes_operational_state = SimpleSNMPSection(
    name="audiocodes_operational_state",
    detect=DETECT_AUDIOCODES,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5003.9.10.10.4.21.1",
        oids=[
            OIDEnd(),
            "8",  # acSysModuleOperationalState
            "4",  # acSysModulePresence
            "9",  # acSysModuleHAStatus
        ],
    ),
    parse_function=parse_audiocodes_operational_state,
)


def discover_audiocodes_operational_state(
    section_audiocodes_module_names: Mapping[str, str] | None,
    section_audiocodes_operational_state: Mapping[str, Module] | None,
) -> DiscoveryResult:
    if not section_audiocodes_module_names or not section_audiocodes_operational_state:
        return

    yield from (
        Service(item=item)
        for item in data_by_item(
            section_audiocodes_module_names,
            section_audiocodes_operational_state,
        )
    )


def check_audiocodes_operational_state(
    item: str,
    section_audiocodes_module_names: Mapping[str, str] | None,
    section_audiocodes_operational_state: Mapping[str, Module] | None,
) -> CheckResult:
    if not section_audiocodes_operational_state or not section_audiocodes_module_names:
        return

    if (
        module := data_by_item(
            section_audiocodes_module_names,
            section_audiocodes_operational_state,
        ).get(item)
    ) is None:
        return

    yield Result(
        state=module.op_state.state,
        summary=f"Operational state: {module.op_state.name}",
    )
    yield Result(
        state=module.presence.state,
        notice=f"Presence: {module.presence.name}",
    )
    yield Result(
        state=module.ha_status.state,
        summary=f"HA status: {module.ha_status.name}",
    )


check_plugin_audiocodes_operational_state = CheckPlugin(
    name="audiocodes_operational_state",
    service_name="AudioCodes Operational State Module %s",
    sections=["audiocodes_module_names", "audiocodes_operational_state"],
    discovery_function=discover_audiocodes_operational_state,
    check_function=check_audiocodes_operational_state,
)
