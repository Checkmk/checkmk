#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Author: Lars Michelsen <lm@mathias-kettner.de>

# Blades:
# '.1.3.6.1.4.1.232.22.2.4.1.1.1.3'  => 'cpqRackServerBladeIndex',
# '.1.3.6.1.4.1.232.22.2.4.1.1.1.4'  => 'cpqRackServerBladeName',
# '.1.3.6.1.4.1.232.22.2.4.1.1.1.6'  => 'cpqRackServerBladePartNumber',
# '.1.3.6.1.4.1.232.22.2.4.1.1.1.7'  => 'cpqRackServerBladeSparePartNumber',
# '.1.3.6.1.4.1.232.22.2.4.1.1.1.8'  => 'cpqRackServerBladePosition',
# '.1.3.6.1.4.1.232.22.2.4.1.1.1.12' => 'cpqRackServerBladePresent',
# '.1.3.6.1.4.1.232.22.2.4.1.1.1.16' => 'cpqRackServerBladeSerialNum',
# '.1.3.6.1.4.1.232.22.2.4.1.1.1.17' => 'cpqRackServerBladeProductId',
# Seems not to be implemented:
# '.1.3.6.1.4.1.232.22.2.4.1.1.1.21' => 'cpqRackServerBladeStatus',
# '.1.3.6.1.4.1.232.22.2.4.1.1.1.22' => 'cpqRackServerBladeFaultMajor',
# '.1.3.6.1.4.1.232.22.2.4.1.1.1.23' => 'cpqRackServerBladeFaultMinor',
# '.1.3.6.1.4.1.232.22.2.4.1.1.1.24' => 'cpqRackServerBladeFaultDiagnosticString',
# '.1.3.6.1.4.1.232.22.2.4.1.1.1.25' => 'cpqRackServerBladePowered',


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
from cmk.plugins.hp_blade.lib import DETECT_HP_BLADE

_PRESENT_MAP: dict[int, str] = {1: "other", 2: "absent", 3: "present"}

_STATUS_MAP: dict[int, tuple[State, str]] = {
    1: (State.CRIT, "Other"),
    2: (State.OK, "Ok"),
    3: (State.WARN, "Degraded"),
    4: (State.CRIT, "Failed"),
}


def parse_hp_blade_blades(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_hp_blade_blades = SimpleSNMPSection(
    name="hp_blade_blades",
    detect=DETECT_HP_BLADE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.22.2.4.1.1.1",
        oids=["3", "12", "21", "17", "4", "16"],
    ),
    parse_function=parse_hp_blade_blades,
)


def discover_hp_blade_blades(section: StringTable) -> DiscoveryResult:
    for line in section:
        if _PRESENT_MAP.get(int(line[1])) == "present":
            yield Service(item=line[0])


def check_hp_blade_blades(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if line[0] != item:
            continue
        present_state = _PRESENT_MAP[int(line[1])]
        if present_state != "present":
            yield Result(
                state=State.CRIT,
                summary=(
                    f"Blade was present but is not available anymore"
                    f" (Present state: {present_state})"
                ),
            )
            return

        # Status field can be an empty string.
        # Seems not to be implemented. The MIB file tells me that this value
        # should represent a state but is empty. So set it to "fake" OK and
        # display the other gathered information.
        try:
            raw_state = int(line[2])
        except (TypeError, ValueError):
            raw_state = 2

        state, state_readable = _STATUS_MAP[raw_state]
        yield Result(
            state=state,
            summary=(
                f"Blade status is {state_readable} "
                f"(Product: {line[3]} Name: {line[4]} S/N: {line[5]})"
            ),
        )
        return


check_plugin_hp_blade_blades = CheckPlugin(
    name="hp_blade_blades",
    service_name="Blade %s",
    discovery_function=discover_hp_blade_blades,
    check_function=check_hp_blade_blades,
)
