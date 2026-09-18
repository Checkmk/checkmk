#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    get_value_store,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType
from cmk.plugins.raritan.lib import STATE_MAPPING, UNIT_MAPPING

_RACK_TYPE_MAPPING = {
    "0": ("temp", "Air"),
    "1": ("temp", "Water"),
    "2": ("fanspeed", ""),
    "3": ("binary", ""),
    "4": ("valve", ""),
}


@dataclass(frozen=True, kw_only=True)
class RackSensor:
    rack_type: str
    rack_unit: str
    rack_value: float | None
    state: tuple[State, str]


type Section = Mapping[str, RackSensor]


def parse_raritan_emx(string_table: StringTable) -> Section:
    parsed = {}
    for rack_id, rack_name, sensor_number, value_text, unit, sensor_state in string_table:
        rack_type, rack_type_readable = _RACK_TYPE_MAPPING[sensor_number]

        extra_name = ""
        if rack_type_readable != "":
            extra_name += " " + rack_type_readable

        rack_name = (f"Rack {rack_id}{extra_name} {rack_name}").replace("DC", "").strip()

        rack_value: float | None
        if rack_type in ["binary", ""]:
            rack_value = None
        elif rack_type == "temp":
            rack_value = float(value_text) / 10
        else:
            rack_value = int(value_text)

        parsed[rack_name] = RackSensor(
            rack_type=rack_type,
            rack_unit=UNIT_MAPPING[unit],
            rack_value=rack_value,
            state=STATE_MAPPING[sensor_state],
        )

    return parsed


snmp_section_raritan_emx = SimpleSNMPSection(
    name="raritan_emx",
    detect=any_of(equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13742.8")),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.9",
        oids=["1.4.1.1.1", "1.4.1.1.4", "1.4.1.1.2", "2.1.1.3", "1.4.1.1.5", "2.1.1.2"],
    ),
    parse_function=parse_raritan_emx,
)


def _discover_by_rack_type(section: Section, rack_type: str) -> DiscoveryResult:
    for rack_name, sensor in section.items():
        if sensor.rack_type == rack_type:
            yield Service(item=rack_name)


#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   |                             main check                               |
#   '----------------------------------------------------------------------'


def discover_raritan_emx_temp(section: Section) -> DiscoveryResult:
    yield from _discover_by_rack_type(section, "temp")


def check_raritan_emx_temp(item: str, params: TempParamType, section: Section) -> CheckResult:
    if "Temperature" in item:
        # old style (pre 1.2.8) item name, convert
        item = "Rack " + item.replace(" Temperature", "")
    elif "Fan Speed" in item:
        yield from _check_fan_speed("Rack " + item.replace(" Fan Speed", ""), section)
        return
    elif "Door Contact" in item:
        yield from _check_binary("Rack " + item.replace(" Door Contact DC", ""), section)
        return

    if (sensor := section.get(item)) is None or sensor.rack_value is None:
        return

    state, state_readable = sensor.state
    yield from check_temperature(
        sensor.rack_value,
        params,
        unique_name=item,
        value_store=get_value_store(),
        dev_unit=sensor.rack_unit,
        dev_status=int(state),
        dev_status_name=state_readable,
    )


check_plugin_raritan_emx = CheckPlugin(
    name="raritan_emx",
    service_name="Temperature %s",
    discovery_function=discover_raritan_emx_temp,
    check_function=check_raritan_emx_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)

# .
#   .--fan-----------------------------------------------------------------.
#   |                            __                                        |
#   |                           / _| __ _ _ __                             |
#   |                          | |_ / _` | '_ \                            |
#   |                          |  _| (_| | | | |                           |
#   |                          |_|  \__,_|_| |_|                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _check_fan_speed(item: str, section: Section) -> CheckResult:
    if (sensor := section.get(item)) is None or sensor.rack_value is None:
        return

    state, state_readable = sensor.state
    yield Result(
        state=state,
        summary=f"Speed: {int(sensor.rack_value)}{sensor.rack_unit}, status: {state_readable}",
    )


def check_raritan_emx_fan(item: str, section: Section) -> CheckResult:
    yield from _check_fan_speed(item, section)


def discover_raritan_emx_fan(section: Section) -> DiscoveryResult:
    yield from _discover_by_rack_type(section, "fanspeed")


check_plugin_raritan_emx_fan = CheckPlugin(
    name="raritan_emx_fan",
    service_name="Fan %s",
    sections=["raritan_emx"],
    discovery_function=discover_raritan_emx_fan,
    check_function=check_raritan_emx_fan,
)


def discover_raritan_emx_binary(section: Section) -> DiscoveryResult:
    yield from _discover_by_rack_type(section, "binary")


# .
#   .--binary--------------------------------------------------------------.
#   |                   _     _                                            |
#   |                  | |__ (_)_ __   __ _ _ __ _   _                     |
#   |                  | '_ \| | '_ \ / _` | '__| | | |                    |
#   |                  | |_) | | | | | (_| | |  | |_| |                    |
#   |                  |_.__/|_|_| |_|\__,_|_|   \__, |                    |
#   |                                            |___/                     |
#   '----------------------------------------------------------------------'


def _check_binary(item: str, section: Section) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return

    state, state_readable = sensor.state
    yield Result(state=state, summary=f"Status: {state_readable}")


def check_raritan_emx_binary(item: str, section: Section) -> CheckResult:
    yield from _check_binary(item, section)


check_plugin_raritan_emx_binary = CheckPlugin(
    name="raritan_emx_binary",
    service_name="Door %s",
    sections=["raritan_emx"],
    discovery_function=discover_raritan_emx_binary,
    check_function=check_raritan_emx_binary,
)
