#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# Author: Lars Michelsen <lm@mathias-kettner.de>

# PSU:
# '.1.3.6.1.4.1.232.22.2.5.1.1.1.3'  => 'cpqRackPowerSupplyIndex',
# '.1.3.6.1.4.1.232.22.2.5.1.1.1.5'  => 'cpqRackPowerSupplySerialNum',
# '.1.3.6.1.4.1.232.22.2.5.1.1.1.6'  => 'cpqRackPowerSupplyPartNumber',
# '.1.3.6.1.4.1.232.22.2.5.1.1.1.7'  => 'cpqRackPowerSupplySparePartNumber',
# '.1.3.6.1.4.1.232.22.2.5.1.1.1.10' => 'cpqRackPowerSupplyCurPwrOutput',
# '.1.3.6.1.4.1.232.22.2.5.1.1.1.14' => 'cpqRackPowerSupplyStatus',
# '.1.3.6.1.4.1.232.22.2.5.1.1.1.15' => 'cpqRackPowerSupplyInputLineStatus',
# '.1.3.6.1.4.1.232.22.2.5.1.1.1.16' => 'cpqRackPowerSupplyPresent',
# '.1.3.6.1.4.1.232.22.2.5.1.1.1.17' => 'cpqRackPowerSupplyCondition',

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.hp_blade.lib import DETECT_HP_BLADE

_PRESENT_MAP = {1: "other", 2: "absent", 3: "present"}
_STATUS_MAP: dict[int, tuple[State, str]] = {
    1: (State.CRIT, "Other"),
    2: (State.OK, "Ok"),
    3: (State.WARN, "Degraded"),
    4: (State.CRIT, "Failed"),
}

_PSU_STATUS = {
    1: "noError",
    2: "generalFailure",
    3: "bistFailure",
    4: "fanFailure",
    5: "tempFailure",
    6: "interlockOpen",
    7: "epromFailed",
    8: "vrefFailed",
    9: "dacFailed",
    10: "ramTestFailed",
    11: "voltageChannelFailed",
    12: "orringdiodeFailed",
    13: "brownOut",
    14: "giveupOnStartup",
    15: "nvramInvalid",
    16: "calibrationTableInvalid",
}

_INPUTLINE_STATUS = {
    1: "noError",
    2: "lineOverVoltage",
    3: "lineUnderVoltage",
    4: "lineHit",
    5: "brownOut",
    6: "linePowerLoss",
}


def parse_hp_blade_psu(string_table: StringTable) -> StringTable:
    return string_table


def discover_hp_blade_psu(section: StringTable) -> DiscoveryResult:
    for line in section:
        if _PRESENT_MAP[int(line[1])] == "present":
            yield Service(item=line[0])


def check_hp_blade_psu(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if line[0] != item:
            continue
        present_state = _PRESENT_MAP[int(line[1])]
        if present_state != "present":
            yield Result(
                state=State.CRIT,
                summary=f"PSU was present but is not available anymore. (Present state: {present_state}",
            )
            return

        state, snmp_state = _STATUS_MAP[int(line[2])]

        if state is State.OK:
            detail_output = f", Output: {line[3]}W"
        else:
            # FIXME: This should probably append strings, not overwrite them...
            detail_output = f" ({_PSU_STATUS[4]})" if int(line[4]) >= 1 else ""
            detail_output = f", Inputline: {_INPUTLINE_STATUS[5]}" if int(line[5]) >= 1 else ""

        yield Result(
            state=state,
            summary=f"PSU is {snmp_state}{detail_output} (S/N: {line[6]})",
        )
        yield Metric("output", float(line[3]))
        return


snmp_section_hp_blade_psu = SimpleSNMPSection(
    name="hp_blade_psu",
    detect=DETECT_HP_BLADE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.22.2.5.1.1.1",
        oids=["3", "16", "17", "10", "14", "15", "5"],
    ),
    parse_function=parse_hp_blade_psu,
)


check_plugin_hp_blade_psu = CheckPlugin(
    name="hp_blade_psu",
    service_name="PSU %s",
    discovery_function=discover_hp_blade_psu,
    check_function=check_hp_blade_psu,
)
