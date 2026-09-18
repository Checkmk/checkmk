#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

from cmk.agent_based.v2 import (
    Attributes,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    InventoryPlugin,
    InventoryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType
from cmk.plugins.perle.lib import DETECT_PERLE, perle_check_alarms


@dataclass
class _Section:
    model: str
    serial: str
    bootloader: str
    firmware: str
    alarms: str
    diagnosis_state: str
    temp: float


def parse_perle_chassis(string_table: StringTable) -> _Section | None:
    if not string_table:
        return None
    model, serial, bootloader, firmware, alarms, diagnosis_state, temp_str = string_table[0]
    return _Section(
        model=model,
        serial=serial,
        bootloader=bootloader,
        firmware=firmware,
        alarms=alarms,
        diagnosis_state=diagnosis_state,
        temp=float(temp_str),
    )


snmp_section_perle_chassis = SimpleSNMPSection(
    name="perle_chassis",
    parse_function=parse_perle_chassis,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1966.21.1.1.1.1.1.1",
        oids=[
            "2",  # PERLE-MCR-MGT-MIB::chassisModelName
            "4",  # PERLE-MCR-MGT-MIB::chassisSerialNumber
            "5",  # PERLE-MCR-MGT-MIB::chassisBootloaderVersion
            "6",  # PERLE-MCR-MGT-MIB::chassisFirmwareVersion
            "7",  # PERLE-MCR-MGT-MIB::chassisOutStandWarnAlarms
            "8",  # PERLE-MCR-MGT-MIB::chassisDiagStatus
            "9",  # PERLE-MCR-MGT-MIB::chassisTemperature
        ],
    ),
    detect=DETECT_PERLE,
)


_MAP_DIAG_STATES = {
    "0": (State.OK, "passed"),
    "1": (State.WARN, "firmware download required"),
    "2": (State.CRIT, "temperature sensor not functional"),
}


def discover_perle_chassis(section: _Section) -> DiscoveryResult:  # noqa: ARG001
    yield Service()


def check_perle_chassis(section: _Section) -> CheckResult:
    state, state_readable = _MAP_DIAG_STATES[section.diagnosis_state]
    yield Result(state=state, summary=f"Diagnostic result: {state_readable}")
    yield perle_check_alarms(section.alarms)


check_plugin_perle_chassis = CheckPlugin(
    name="perle_chassis",
    service_name="Chassis status",
    discovery_function=discover_perle_chassis,
    check_function=check_perle_chassis,
)


def discover_perle_chassis_temp(section: _Section) -> DiscoveryResult:  # noqa: ARG001
    yield Service(item="chassis")


def check_perle_chassis_temp(item: str, params: TempParamType, section: _Section) -> CheckResult:  # noqa: ARG001
    yield from check_temperature(
        reading=section.temp,
        params=params,
        unique_name="perle_chassis_temp",
        value_store=get_value_store(),
    )


check_plugin_perle_chassis_temp = CheckPlugin(
    name="perle_chassis_temp",
    sections=["perle_chassis"],
    service_name="Temperature %s",
    discovery_function=discover_perle_chassis_temp,
    check_function=check_perle_chassis_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)


def inventorize_perle_chassis(section: _Section) -> InventoryResult:
    yield Attributes(
        path=["hardware", "chassis"],
        inventory_attributes={
            "serial": section.serial,
            "model": section.model,
            "bootloader": section.bootloader,
            "firmware": section.firmware,
        },
    )


inventory_plugin_perle_chassis = InventoryPlugin(
    name="perle_chassis",
    inventory_function=inventorize_perle_chassis,
)
