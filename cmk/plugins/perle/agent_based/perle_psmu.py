#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import contextlib
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    InventoryPlugin,
    InventoryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
    TableRow,
)
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingWithState
from cmk.plugins.perle.lib import DETECT_PERLE

# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.2.1.1 1 --> PERLE-MCR-MGT-MIB::mcrPsmuIndex.1.a
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.2.1.2 2 --> PERLE-MCR-MGT-MIB::mcrPsmuIndex.1.b
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.3.1.1 MCR-ACPWR --> PERLE-MCR-MGT-MIB::mcrPsmuModelName.1.a
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.3.1.2 MCR-ACPWR --> PERLE-MCR-MGT-MIB::mcrPsmuModelName.1.b
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.4.1.1
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.4.1.2
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.5.1.1 104-101015T10175 --> PERLE-MCR-MGT-MIB::mcrPsmuPsuSerialNumber.1.a
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.5.1.2 104-101015T10177 --> PERLE-MCR-MGT-MIB::mcrPsmuPsuSerialNumber.1.b
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.9.1.1 1 --> PERLE-MCR-MGT-MIB::mcrPsmuPsuStatus.1.a
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.9.1.2 1 --> PERLE-MCR-MGT-MIB::mcrPsmuPsuStatus.1.b
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.10.1.1 12.05 --> PERLE-MCR-MGT-MIB::mcrPsmuPsuVoltage.1.a
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.10.1.2 12.05 --> PERLE-MCR-MGT-MIB::mcrPsmuPsuVoltage.1.b
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.11.1.1 6.75 --> PERLE-MCR-MGT-MIB::mcrPsmuPsuPowerUsage.1.a
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.11.1.2 6.75 --> PERLE-MCR-MGT-MIB::mcrPsmuPsuPowerUsage.1.b
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.12.1.1 1 --> PERLE-MCR-MGT-MIB::mcrPsmuFanStatus.1.a
# .1.3.6.1.4.1.1966.21.1.1.1.1.2.1.12.1.2 1 --> PERLE-MCR-MGT-MIB::mcrPsmuFanStatus.1.b

Section = Mapping[str, Mapping[str, Any]]

_MAP_STATES = {
    "0": (2, "not present"),
    "1": (0, "good"),
    "2": (2, "fail"),
}


def parse_perle_psmu(string_table: StringTable) -> Section:
    parsed: dict[str, dict[str, Any]] = {}
    for (
        index,
        modelname,
        descr,
        serial,
        psu_status,
        voltage_str,
        power_str,
        fan_status,
    ) in string_table:
        parsed.setdefault(
            index,
            {
                "model": modelname,
                "descr": descr,
                "serial": serial,
                "fanstate": _MAP_STATES.get(fan_status, (3, "unknown[%s]" % fan_status)),
                "psustate": _MAP_STATES.get(psu_status, (3, "unknown[%s]" % psu_status)),
            },
        )
        for what, value_str in [("power", power_str), ("voltage", voltage_str)]:
            with contextlib.suppress(ValueError):
                parsed[index].setdefault(what, float(value_str))

    return parsed


snmp_section_perle_psmu = SimpleSNMPSection(
    name="perle_psmu",
    parse_function=parse_perle_psmu,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1966.21.1.1.1.1.2.1",
        oids=[
            "2",  # PERLE-MCR-MGT-MIB::mcrPsmuIndex
            "3",  # PERLE-MCR-MGT-MIB::mcrPsmuModelName
            "4",  # PERLE-MCR-MGT-MIB::mcrPsmuModelDesc
            "5",  # PERLE-MCR-MGT-MIB::mcrPsmuPsuSerialNumber
            "9",  # PERLE-MCR-MGT-MIB::mcrPsmuPsuStatus
            "10",  # PERLE-MCR-MGT-MIB::mcrPsmuPsuVoltageUsage
            "11",  # PERLE-MCR-MGT-MIB::mcrPsmuPsuPowerUsage
            "12",  # PERLE-MCR-MGT-MIB::mcrPsmuFanStatus
        ],
    ),
    detect=DETECT_PERLE,
)


def _discover_perle_psmu(section: Section, what_state: str) -> DiscoveryResult:
    for unit, values in section.items():
        if values[what_state][1] != "not present":
            yield Service(item=unit)


def discover_perle_psmu(section: Section) -> DiscoveryResult:
    yield from _discover_perle_psmu(section, "psustate")


def discover_perle_psmu_fan(section: Section) -> DiscoveryResult:
    yield from _discover_perle_psmu(section, "fanstate")


def check_perle_psmu_powersupplies(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (data := section.get(item)) is None:
        return
    state, state_readable = data["psustate"]
    yield Result(state=State(state), summary=f"Status: {state_readable}")
    yield from check_elphase(
        params,
        ElPhase(
            voltage=ReadingWithState(value=data["voltage"]) if "voltage" in data else None,
            power=ReadingWithState(value=data["power"]) if "power" in data else None,
        ),
    )


def check_perle_psmu_fans(item: str, section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return
    state, state_readable = data["fanstate"]
    yield Result(state=State(state), summary=f"Status: {state_readable}")


check_plugin_perle_psmu = CheckPlugin(
    name="perle_psmu",
    service_name="Power supply %s",
    discovery_function=discover_perle_psmu,
    check_function=check_perle_psmu_powersupplies,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)


check_plugin_perle_psmu_fan = CheckPlugin(
    name="perle_psmu_fan",
    sections=["perle_psmu"],
    service_name="Fan %s",
    discovery_function=discover_perle_psmu_fan,
    check_function=check_perle_psmu_fans,
)


def inventorize_perle_psmu(section: Section) -> InventoryResult:
    for psu_index, data in section.items():
        yield TableRow(
            path=["hardware", "components", "psus"],
            key_columns={
                "index": psu_index,
            },
            inventory_columns={
                "description": data["descr"],
                "model": data["model"],
                "serial": data["serial"],
            },
            status_columns={},
        )


inventory_plugin_perle_psmu = InventoryPlugin(
    name="perle_psmu",
    inventory_function=inventorize_perle_psmu,
)
