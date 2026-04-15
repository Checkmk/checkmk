#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)
from cmk.plugins.lib.elphase import check_elphase, ElPhase
from cmk.plugins.lib.temperature import check_temperature, TempParamType

Section = dict[str, Any]


def parse_orion_system(string_table: StringTable) -> Section | None:
    if not string_table:
        return None

    map_charge_states: dict[str, tuple[int, str]] = {
        "1": (0, "float charging"),
        "2": (0, "discharge"),
        "3": (0, "equalize"),
        "4": (0, "boost"),
        "5": (0, "battery test"),
        "6": (0, "recharge"),
        "7": (0, "separate charge"),
        "8": (0, "event control charge"),
    }

    (
        system_voltage,
        load_current,
        battery_current,
        battery_temp,
        charge_state,
        _battery_current_limit,
        rectifier_current,
        system_power,
    ) = string_table[0]

    temperature: dict[str, float] = {}
    if battery_temp != "2147483647":
        temperature["Battery"] = int(battery_temp) * 0.1

    electrical: dict[str, dict[str, float]] = {}
    for what, value, factor in [
        ("voltage", system_voltage, 0.01),
        ("current", load_current, 0.1),
        ("power", system_power, 1),
    ]:
        if value != "2147483647":
            system_data = electrical.setdefault("System", {})
            system_data[what] = int(value) * factor

    for item, value in [
        ("Battery", battery_current),
        ("Rectifier", rectifier_current),
    ]:
        if value != "2147483647":
            item_data = electrical.setdefault(item, {})
            item_data["current"] = int(battery_temp) * 0.1

    return {
        "charging": {
            "Battery": map_charge_states.get(charge_state, (3, f"unknown[{charge_state}]"))
        },
        "temperature": temperature,
        "electrical": electrical,
    }


def discover_orion_system_temp(section: Section) -> DiscoveryResult:
    for entity in section["temperature"]:
        yield Service(item=entity)


def check_orion_system_temp(item: str, params: TempParamType, section: Section) -> CheckResult:
    if item in section["temperature"]:
        yield from check_temperature(
            section["temperature"][item],
            params,
            unique_name=f"orion_system_temp.{item}",
            value_store=get_value_store(),
        )


snmp_section_orion_system = SimpleSNMPSection(
    name="orion_system",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.20246"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20246.2.3.1.1.1.2.3",
        oids=["1", "2", "3", "4", "5", "6", "7", "8"],
    ),
    parse_function=parse_orion_system,
)


check_plugin_orion_system = CheckPlugin(
    name="orion_system",
    service_name="Temperature %s",
    discovery_function=discover_orion_system_temp,
    check_function=check_orion_system_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)


def discover_orion_system_charging(section: Section) -> DiscoveryResult:
    for entity in section["charging"]:
        yield Service(item=entity)


def check_orion_system_charging(item: str, section: Section) -> CheckResult:
    if item in section["charging"]:
        state_int, state_readable = section["charging"][item]
        yield Result(state=State(state_int), summary=f"Status: {state_readable}")


check_plugin_orion_system_charging = CheckPlugin(
    name="orion_system_charging",
    service_name="Charge %s",
    sections=["orion_system"],
    discovery_function=discover_orion_system_charging,
    check_function=check_orion_system_charging,
)


def discover_orion_system_electrical(section: Section) -> DiscoveryResult:
    for entity in section["electrical"]:
        yield Service(item=entity)


def check_orion_system_electrical(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    yield from check_elphase(params, ElPhase.from_dict(section["electrical"].get(item, {})))


check_plugin_orion_system_dc = CheckPlugin(
    name="orion_system_dc",
    service_name="Direct Current %s",
    sections=["orion_system"],
    discovery_function=discover_orion_system_electrical,
    check_function=check_orion_system_electrical,
    check_ruleset_name="ups_outphase",
    check_default_parameters={},
)
