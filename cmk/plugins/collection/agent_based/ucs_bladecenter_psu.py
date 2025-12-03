#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingWithState
from cmk.plugins.lib.temperature import (
    aggregate_temperature_results,
    check_temperature,
    TemperatureSensor,
    TempParamDict,
)
from cmk.plugins.ucs_bladecenter import lib as ucs_bladecenter

# <<<ucs_bladecenter_psu:sep(9)>>>
# equipmentPsuInputStats  Dn sys/switch-A/psu-2/input-stats       Current 0.656250        PowerAvg 153.335938     Voltage 231.500000
# equipmentPsuStats       Dn sys/chassis-1/psu-1/stats    AmbientTemp 17.000000   Output12vAvg 12.008000  Output3v3Avg 3.336000

type Section = MutableMapping[str, MutableMapping[str, str]]


def parse_ucs_bladecenter_psu(string_table: StringTable) -> Section:
    data = ucs_bladecenter.generic_parse(string_table)
    psu: Section = {}

    def get_item_name(key: str) -> str:
        tokens = key.split("/")
        tokens[1] = tokens[1].replace("psu-", " Module ")
        tokens = [x[0].upper() + x[1:] for x in tokens]
        return "".join(tokens).replace("-", " ")

    for component, key_low, key_high in [
        ("equipmentPsuInputStats", 4, -12),
        ("equipmentPsuStats", 4, -6),
    ]:
        for key, values in data.get(component, {}).items():
            name = get_item_name(key[key_low:key_high])
            del values["Dn"]
            psu.setdefault(name, {}).update(values)

    return psu


agent_section_ucs_bladecenter_psu = AgentSection(
    name="ucs_bladecenter_psu",
    parse_function=parse_ucs_bladecenter_psu,
)


# .
#   .--Chassis Volt.-------------------------------------------------------.
#   |         ____ _                   _      __     __    _ _             |
#   |        / ___| |__   __ _ ___ ___(_)___  \ \   / /__ | | |_           |
#   |       | |   | '_ \ / _` / __/ __| / __|  \ \ / / _ \| | __|          |
#   |       | |___| | | | (_| \__ \__ \ \__ \   \ V / (_) | | |_ _         |
#   |        \____|_| |_|\__,_|___/___/_|___/    \_/ \___/|_|\__(_)        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_ucs_bladecenter_psu(section: Section) -> DiscoveryResult:
    for key in section:
        if key.startswith("Chassis"):
            yield Service(item=key)


def check_ucs_bladecenter_psu(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (psu := section.get(item)):
        return
    value_3v = float(psu["Output3v3Avg"])
    value_12v = float(psu["Output12vAvg"])

    power_save_mode = value_3v == 0.0 and value_12v == 0.0

    yield from check_levels_v1(
        value_3v,
        metric_name="3_3v",
        levels_upper=None if power_save_mode else params["levels_3v_upper"],
        levels_lower=None if power_save_mode else params["levels_3v_lower"],
        render_func=lambda v: "%.2f V" % v,
        label="Output 3.3V-Average",
    )
    yield from check_levels_v1(
        value_12v,
        metric_name="12v",
        levels_upper=None if power_save_mode else params["levels_12v_upper"],
        levels_lower=None if power_save_mode else params["levels_12v_lower"],
        render_func=lambda v: "%.2f V" % v,
        label="Output 12V-Average",
    )

    if power_save_mode:
        yield Result(state=State.OK, summary="Assuming 'Power Save Mode'")


check_plugin_ucs_bladecenter_psu = CheckPlugin(
    name="ucs_bladecenter_psu",
    service_name="Voltage %s",
    discovery_function=discover_ucs_bladecenter_psu,
    check_function=check_ucs_bladecenter_psu,
    check_ruleset_name="ucs_bladecenter_chassis_voltage",
    check_default_parameters={
        "levels_3v_lower": (3.25, 3.20),
        "levels_3v_upper": (3.4, 3.45),
        "levels_12v_lower": (11.9, 11.8),
        "levels_12v_upper": (12.1, 12.2),
    },
)

# .
#   .--Power Supply--------------------------------------------------------.
#   |    ____                          ____                    _           |
#   |   |  _ \ _____      _____ _ __  / ___| _   _ _ __  _ __ | |_   _     |
#   |   | |_) / _ \ \ /\ / / _ \ '__| \___ \| | | | '_ \| '_ \| | | | |    |
#   |   |  __/ (_) \ V  V /  __/ |     ___) | |_| | |_) | |_) | | |_| |    |
#   |   |_|   \___/ \_/\_/ \___|_|    |____/ \__,_| .__/| .__/|_|\__, |    |
#   |                                             |_|   |_|      |___/     |
#   '----------------------------------------------------------------------'


def discover_ucs_bladecenter_psu_switch_power(section: Section) -> DiscoveryResult:
    for key in section:
        if key.startswith("Switch"):
            yield Service(item=key)


def check_ucs_bladecenter_psu_switch_power(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (psu := section.get(item)):
        return

    current = ReadingWithState(value=float(current)) if (current := psu.get("Current")) else None
    power = ReadingWithState(value=float(power)) if (power := psu.get("PowerAvg")) else None
    voltage = ReadingWithState(value=float(voltage)) if (voltage := psu.get("Voltage")) else None

    if all(x is not None for x in (current, power, voltage)):
        yield from check_elphase(params, ElPhase(current=current, power=power, voltage=voltage))


check_plugin_ucs_bladecenter_psu_switch_power = CheckPlugin(
    name="ucs_bladecenter_psu_switch_power",
    service_name="Power Supply %s",
    sections=["ucs_bladecenter_psu"],
    discovery_function=discover_ucs_bladecenter_psu_switch_power,
    check_function=check_ucs_bladecenter_psu_switch_power,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)

# .
#   .--Temperature---------------------------------------------------------.
#   |     _____                                   _                        |
#   |    |_   _|__ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |      | |/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |      | |  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      |_|\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'


def discover_ucs_bladecenter_psu_chassis_temp(section: Section) -> DiscoveryResult:
    for key, values in section.items():
        if key.startswith("Chassis") and values.get("AmbientTemp"):
            yield Service(item="Ambient " + " ".join(key.split()[:2]))


def _check_ucs_bladecenter_psu_chassis_temp(
    item: str,
    params: TempParamDict,
    section: Section,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    sensor_item = item[8:]  # drop "Ambient "
    sensor_list: list[TemperatureSensor] = []
    for key, values in sorted(section.items()):
        if not key.startswith(sensor_item) or "AmbientTemp" not in values:
            continue
        temp = float(values["AmbientTemp"])
        sensor = TemperatureSensor(
            id=f"Module {key.split()[-1]}",
            temp=temp,
            result=check_temperature(temp, params).reading,
        )
        sensor_list.append(sensor)
    yield from aggregate_temperature_results(sensor_list, params, value_store)


def check_ucs_bladecenter_psu_chassis_temp(
    item: str, params: TempParamDict, section: Section
) -> CheckResult:
    yield from _check_ucs_bladecenter_psu_chassis_temp(item, params, section, get_value_store())


check_plugin_ucs_bladecenter_psu_chassis_temp = CheckPlugin(
    name="ucs_bladecenter_psu_chassis_temp",
    service_name="Temperature %s",
    sections=["ucs_bladecenter_psu"],
    discovery_function=discover_ucs_bladecenter_psu_chassis_temp,
    check_function=check_ucs_bladecenter_psu_chassis_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (35.0, 40.0),
    },
)
