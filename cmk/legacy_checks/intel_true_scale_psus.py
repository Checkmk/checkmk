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
from cmk.plugins.intel.lib import DETECT_INTEL_TRUE_SCALE
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingWithState


@dataclass(frozen=True)
class Psu:
    state: State
    state_readable: str
    source: str
    voltage: float
    power: float


Section = Mapping[str, Psu]

# .1.3.6.1.4.1.10222.2.1.4.7.1.2.2.1 Power Supply 201 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyDescription.2.1
# .1.3.6.1.4.1.10222.2.1.4.7.1.2.3.2 Power Supply 202 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyDescription.3.2
# .1.3.6.1.4.1.10222.2.1.4.7.1.2.4.3 Power Supply 203 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyDescription.4.3
# .1.3.6.1.4.1.10222.2.1.4.7.1.2.5.4 Power Supply 204 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyDescription.5.4
# .1.3.6.1.4.1.10222.2.1.4.7.1.3.2.1 6 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyOperStatus.2.1
# .1.3.6.1.4.1.10222.2.1.4.7.1.3.3.2 6 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyOperStatus.3.2
# .1.3.6.1.4.1.10222.2.1.4.7.1.3.4.3 6 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyOperStatus.4.3
# .1.3.6.1.4.1.10222.2.1.4.7.1.3.5.4 6 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyOperStatus.5.4
# .1.3.6.1.4.1.10222.2.1.4.7.1.4.2.1 1 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyInputSource.2.1
# .1.3.6.1.4.1.10222.2.1.4.7.1.4.3.2 1 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyInputSource.3.2
# .1.3.6.1.4.1.10222.2.1.4.7.1.4.4.3 1 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyInputSource.4.3
# .1.3.6.1.4.1.10222.2.1.4.7.1.4.5.4 1 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyInputSource.5.4
# .1.3.6.1.4.1.10222.2.1.4.7.1.5.2.1 0 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyVoltage.2.1
# .1.3.6.1.4.1.10222.2.1.4.7.1.5.3.2 0 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyVoltage.3.2
# .1.3.6.1.4.1.10222.2.1.4.7.1.5.4.3 0 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyVoltage.4.3
# .1.3.6.1.4.1.10222.2.1.4.7.1.5.5.4 0 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyVoltage.5.4
# .1.3.6.1.4.1.10222.2.1.4.7.1.6.2.1 0 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyOutputPower.2.1
# .1.3.6.1.4.1.10222.2.1.4.7.1.6.3.2 0 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyOutputPower.3.2
# .1.3.6.1.4.1.10222.2.1.4.7.1.6.4.3 0 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyOutputPower.4.3
# .1.3.6.1.4.1.10222.2.1.4.7.1.6.5.4 0 --> ICS-CHASSIS-MIB::icsChassisPowerSupplyOutputPower.5.4


def parse_intel_true_scale_psus(string_table: StringTable) -> Section:
    map_states = {
        "1": (State.UNKNOWN, "unknown"),
        "2": (State.UNKNOWN, "disabled"),
        "3": (State.CRIT, "failed"),
        "4": (State.WARN, "warning"),
        "5": (State.OK, "standby"),
        "6": (State.OK, "engaged"),
        "7": (State.OK, "redundant"),
        "8": (State.UNKNOWN, "not present"),
    }
    map_sources = {
        "0": "invalid",
        "1": "ac line",
        "2": "dc line",
        "3": "none",
        "4": "unknown",
    }

    parsed: dict[str, Psu] = {}
    for descr, operstate, source, voltage_str, power_str in string_table:
        name = descr.replace("Power Supply", "").strip()
        state, state_readable = map_states[operstate]

        parsed.setdefault(
            name,
            Psu(
                state=state,
                state_readable=state_readable,
                source=map_sources[source],
                voltage=float(voltage_str),
                power=float(power_str),
            ),
        )

    return parsed


def discover_intel_true_scale_psus(section: Section) -> DiscoveryResult:
    for psu, values in section.items():
        if values.state_readable not in ["not present", "disabled"]:
            yield Service(item=psu)


def check_intel_true_scale_psus(
    item: str, params: Mapping[str, object], section: Section
) -> CheckResult:
    if (data := section.get(item)) is None:
        return

    yield Result(
        state=data.state,
        summary=f"Operational status: {data.state_readable}, Source: {data.source}",
    )

    yield from check_elphase(
        params,
        ElPhase(
            voltage=ReadingWithState(value=data.voltage),
            power=ReadingWithState(value=data.power),
        ),
    )


snmp_section_intel_true_scale_psus = SimpleSNMPSection(
    name="intel_true_scale_psus",
    detect=DETECT_INTEL_TRUE_SCALE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.10222.2.1.4.7.1",
        oids=["2", "3", "4", "5", "6"],
    ),
    parse_function=parse_intel_true_scale_psus,
)


check_plugin_intel_true_scale_psus = CheckPlugin(
    name="intel_true_scale_psus",
    service_name="Power supply %s",
    discovery_function=discover_intel_true_scale_psus,
    check_function=check_intel_true_scale_psus,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)
