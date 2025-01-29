#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import NamedTuple

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.netextreme import DETECT_NETEXTREME


class PowerInformation(NamedTuple):
    pse_power: str | None  # there are cases where this is not present in the walk
    input_line_voltage: str
    output_watts: (
        str | None
    )  # there are cases where this is not present in the walk, because only newer devices have it


@dataclass
class VSPSwitchPowerSupply:
    id: str
    operational_status: str
    power_information: PowerInformation | None = None


VSPSwitchesSection = Mapping[str, VSPSwitchPowerSupply]

_MAP_POWER_SUPPLY_STATUS = {
    "1": (State.UNKNOWN, "unknown - status can not be determined"),
    "2": (State.WARN, "empty - power supply not installed"),
    "3": (State.OK, "up - present and supplying power"),
    "4": (State.CRIT, "down - present, but failure indicated"),
}

_MAP_INPUT_VOLTAGE = {
    "0": "unknown",
    "1": "low110v",
    "2": "high220v",
    "3": "minus48v",
    "4": "ac110vOr220v",
    "5": "dc",
}


def parse_vsp_switches_power_supply(string_table: Sequence[StringTable]) -> VSPSwitchesSection:
    power_supplies = {
        line[0]: VSPSwitchPowerSupply(
            id=line[0],
            operational_status=line[1],
        )
        for line in string_table[0]
    }

    for line in string_table[1]:
        if line[0] not in power_supplies:
            continue

        power_supplies[line[0]].power_information = PowerInformation(
            pse_power=line[1],
            input_line_voltage=_MAP_INPUT_VOLTAGE[line[2]],
            output_watts=line[3] or None,
        )

    return power_supplies


snmp_section_extreme_vsp_switches_power_supply = SNMPSection(
    name="extreme_vsp_switches_power_supply",
    parse_function=parse_vsp_switches_power_supply,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.2272.1.4.8.1.1",
            oids=[
                "1",  # rcChasPowerSupplyId
                "2",  # rcChasPowerSupplyOperStatus
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2272.1.4.8.2.1",
            oids=[
                "1",  # rcChasPowerSupplyDetailId
                "7",  # rcChasPowerSupplyDetailPsePower
                "8",  # rcChasPowerSupplyDetailInputLineVoltage
                "10",  # rcChasPowerSupplyDetailOutputWatts
            ],
        ),
    ],
    detect=DETECT_NETEXTREME,
)


def discover_vsp_switches_power_supply(section: VSPSwitchesSection) -> DiscoveryResult:
    for vsp_switch in section:
        yield Service(item=vsp_switch)


def check_vsp_switches_power_supply(
    item: str,
    section: VSPSwitchesSection,
) -> CheckResult:
    if (vsp_switch := section.get(item)) is None:
        return

    state, state_readable = _MAP_POWER_SUPPLY_STATUS.get(
        vsp_switch.operational_status,
        (State.UNKNOWN, f"Unknown power supply status:{vsp_switch.operational_status}"),
    )
    yield Result(state=state, summary=f"Operational status: {state_readable}")

    if vsp_switch.power_information:
        yield Result(
            state=State.OK,
            summary=f"Input Line Voltage {vsp_switch.power_information.input_line_voltage}",
        )
    else:
        yield Result(
            state=State.OK, summary="No power information available for this power supply."
        )

    if vsp_switch.power_information and vsp_switch.power_information.output_watts:
        yield Result(
            state=State.OK, summary=f"Output Watts: {vsp_switch.power_information.output_watts}"
        )

    if vsp_switch.power_information and vsp_switch.power_information.pse_power:
        yield Result(state=State.OK, summary=f"PSE Power: {vsp_switch.power_information.pse_power}")


check_plugin_extreme_vsp_switches_power_supply = CheckPlugin(
    name="extreme_vsp_switches_power_supply",
    service_name="VSP Switch Power Supply %s",
    discovery_function=discover_vsp_switches_power_supply,
    check_function=check_vsp_switches_power_supply,
)
