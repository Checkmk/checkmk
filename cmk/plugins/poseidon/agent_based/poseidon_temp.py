#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


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
from cmk.plugins.lib.temperature import check_temperature, TempParamType

Section = Mapping[str, Mapping[str, Any]]


def parse_poseidon_temp(string_table: StringTable) -> Section | None:
    parsed = {}
    if not string_table:
        return None
    for name, state, value_string in string_table:
        try:
            temp = float(value_string.replace("C", ""))
        except ValueError:
            temp = None
        parsed[name] = {"temp": temp, "status": state}
    return parsed


def check_poseidon_temp(item: str, params: TempParamType, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    sensor_states = {
        "0": "invalid",
        "1": "normal",
        "2": "alarmstate",
        "3": "alarm",
    }
    sensor_state_value = data.get("status")
    sensor_state_txt = sensor_states.get(sensor_state_value) if sensor_state_value else None
    mk_status = State.OK
    if sensor_state_value != "1":
        mk_status = State.CRIT
    yield Result(state=mk_status, summary=f"Sensor {item}, State {sensor_state_txt}")

    temp = data.get("temp")
    if temp:
        yield from check_temperature(
            temp,
            params,
            unique_name=f"poseidon_temp_{item.replace(' ', '_')}",
            value_store=get_value_store(),
        )
    else:
        yield Result(state=State.UNKNOWN, summary=f"No data for Sensor {item} found")


def discover_poseidon_temp(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


snmp_section_poseidon_temp = SimpleSNMPSection(
    name="poseidon_temp",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.21796.3"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21796.3.3.3.1",
        oids=["2", "4", "5"],
    ),
    parse_function=parse_poseidon_temp,
)


check_plugin_poseidon_temp = CheckPlugin(
    name="poseidon_temp",
    service_name="Temperatur: %s",
    discovery_function=discover_poseidon_temp,
    check_function=check_poseidon_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
