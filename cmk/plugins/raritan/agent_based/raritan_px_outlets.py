#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingWithState

# .1.3.6.1.4.1.13742.4.1.2.2.1.1.1 1 --> PDU-MIB::outletIndex.1
# .1.3.6.1.4.1.13742.4.1.2.2.1.1.3 3 --> PDU-MIB::outletIndex.3
# .1.3.6.1.4.1.13742.4.1.2.2.1.1.4 4 --> PDU-MIB::outletIndex.4
# .1.3.6.1.4.1.13742.4.1.2.2.1.2.1 Outlet 1 --> PDU-MIB::outletLabel.1
# .1.3.6.1.4.1.13742.4.1.2.2.1.2.3 Outlet 3 --> PDU-MIB::outletLabel.3
# .1.3.6.1.4.1.13742.4.1.2.2.1.2.4 Outlet 4 --> PDU-MIB::outletLabel.4
# .1.3.6.1.4.1.13742.4.1.2.2.1.3.1 1 --> PDU-MIB::outletOperationalState.1
# .1.3.6.1.4.1.13742.4.1.2.2.1.3.3 1 --> PDU-MIB::outletOperationalState.3
# .1.3.6.1.4.1.13742.4.1.2.2.1.3.4 0 --> PDU-MIB::outletOperationalState.4
# .1.3.6.1.4.1.13742.4.1.2.2.1.4.1 0 --> PDU-MIB::outletCurrent.1
# .1.3.6.1.4.1.13742.4.1.2.2.1.4.3 6854 --> PDU-MIB::outletCurrent.3
# .1.3.6.1.4.1.13742.4.1.2.2.1.4.4 0 --> PDU-MIB::outletCurrent.4
# .1.3.6.1.4.1.13742.4.1.2.2.1.6.1 222000 --> PDU-MIB::outletVoltage.1
# .1.3.6.1.4.1.13742.4.1.2.2.1.6.3 222000 --> PDU-MIB::outletVoltage.3
# .1.3.6.1.4.1.13742.4.1.2.2.1.6.4 222000 --> PDU-MIB::outletVoltage.4
# .1.3.6.1.4.1.13742.4.1.2.2.1.7.1 0 --> PDU-MIB::outletActivePower.1
# .1.3.6.1.4.1.13742.4.1.2.2.1.7.3 1475 --> PDU-MIB::outletActivePower.3
# .1.3.6.1.4.1.13742.4.1.2.2.1.7.4 0 --> PDU-MIB::outletActivePower.4
# .1.3.6.1.4.1.13742.4.1.2.2.1.8.1 0 --> PDU-MIB::outletApparentPower.1
# .1.3.6.1.4.1.13742.4.1.2.2.1.8.3 1542 --> PDU-MIB::outletApparentPower.3
# .1.3.6.1.4.1.13742.4.1.2.2.1.8.4 0 --> PDU-MIB::outletApparentPower.4
# .1.3.6.1.4.1.13742.4.1.2.2.1.31.1 0 --> PDU-MIB::outletWattHours.1
# .1.3.6.1.4.1.13742.4.1.2.2.1.31.3 0 --> PDU-MIB::outletWattHours.3
# .1.3.6.1.4.1.13742.4.1.2.2.1.31.4 0 --> PDU-MIB::outletWattHours.4

_STATE_MAPPING = {
    "-1": (State.CRIT, "error"),
    "0": (State.CRIT, "off"),
    "1": (State.OK, "on"),
    "2": (State.OK, "cycling"),
}


@dataclass(frozen=True, kw_only=True)
class Outlet:
    label: str
    elphase: ElPhase


type Section = Mapping[str, Outlet]


def parse_raritan_px_outlets(string_table: StringTable) -> Section:
    parsed = {}
    for (
        index,
        label,
        state,
        current_str,
        voltage_str,
        power_str,
        appower_str,
        energy_str,
    ) in string_table:
        parsed[index] = Outlet(
            label=label,
            elphase=ElPhase(
                device_state=_STATE_MAPPING.get(state, (State.UNKNOWN, "unknown")),
                current=ReadingWithState(value=float(current_str) / 1000),
                voltage=ReadingWithState(value=float(voltage_str) / 1000),
                power=ReadingWithState(value=float(power_str)),
                appower=ReadingWithState(value=float(appower_str)),
                energy=ReadingWithState(value=float(energy_str)),
            ),
        )

    return parsed


def discover_raritan_px_outlets(section: Section) -> DiscoveryResult:
    for index, outlet in section.items():
        if outlet.elphase.device_state is not None and outlet.elphase.device_state[1] == "on":
            yield Service(item=index)


def check_raritan_px_outlets(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (outlet := section.get(item)) is None:
        return
    if outlet.label:
        yield Result(state=State.OK, summary=f"[{outlet.label}]")
    yield from check_elphase(params, outlet.elphase)


snmp_section_raritan_px_outlets = SimpleSNMPSection(
    name="raritan_px_outlets",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13742.4"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.4.1.2.2.1",
        oids=["1", "2", "3", "4", "6", "7", "8", "31"],
    ),
    parse_function=parse_raritan_px_outlets,
)


check_plugin_raritan_px_outlets = CheckPlugin(
    name="raritan_px_outlets",
    service_name="Outlet %s",
    discovery_function=discover_raritan_px_outlets,
    check_function=check_raritan_px_outlets,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)
