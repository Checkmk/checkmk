#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping
from typing import Any

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
from cmk.plugins.lib.temperature import (
    aggregate_temperature_results,
    check_temperature,
    TemperatureSensor,
    TempParamDict,
)
from cmk.plugins.ucs_bladecenter import lib as ucs_bladecenter

# <<ucs_bladecenter_fans:sep(9)>>>
# equipmentNetworkElementFanStats Dn sys/switch-A/fan-module-1-1/fan-1/stats      SpeedAvg 8542
# equipmentFanModuleStats Dn sys/chassis-2/fan-module-1-1/stats   AmbientTemp 29.000000
# equipmentFan    Dn sys/chassis-1/fan-module-1-1/fan-1   Model N20-FAN5  OperState operable
# equipmentFanStats       Dn sys/chassis-2/fan-module-1-1/fan-1/stats     SpeedAvg 3652

type Section = Mapping[str, Mapping[str, str]]


def parse_ucs_bladecenter_fans(string_table: StringTable) -> Section:
    data = ucs_bladecenter.generic_parse(string_table)
    fans = dict[str, dict[str, str]]()

    def get_item_name(key: str) -> str:
        tokens = key.split("/")
        tokens[1] = tokens[1].replace("fan-module-", "Module ").replace("-", ".")
        tokens = [x[0].upper() + x[1:] for x in tokens]
        if len(tokens) > 2:
            tokens[2] = tokens[2].replace("fan-", ".")
        return " ".join(tokens).replace("-", " ")

    for component, key_low, key_high in [
        ("equipmentNetworkElementFanStats", 4, -6),
        ("equipmentFanModuleStats", 4, -6),
        ("equipmentFan", 4, 100),
        ("equipmentFanStats", 4, -6),
    ]:
        for key, values in data.get(component, {}).items():
            fan = key[key_low:key_high]
            del values["Dn"]
            name = get_item_name(fan)
            fans.setdefault(name, {}).update(values)

    return fans


agent_section_ucs_bladecenter_fans = AgentSection(
    name="ucs_bladecenter_fans",
    parse_function=parse_ucs_bladecenter_fans,
)


#   .--Fans----------------------------------------------------------------.
#   |                         _____                                        |
#   |                        |  ___|_ _ _ __  ___                          |
#   |                        | |_ / _` | '_ \/ __|                         |
#   |                        |  _| (_| | | | \__ \                         |
#   |                        |_|  \__,_|_| |_|___/                         |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_ucs_bladecenter_fans(section: Section) -> DiscoveryResult:
    for key, values in section.items():
        if "SpeedAvg" in values:
            yield Service(item=" ".join(key.split()[:2]))


def check_ucs_bladecenter_fans(item: str, section: Section) -> CheckResult:
    my_fans = {}
    for key, values in section.items():
        if key.startswith(item) and "OperState" in values:
            my_fans[key] = values

    if not my_fans:
        yield Result(state=State.UNKNOWN, summary="Fan statistics not available")
        return

    yield Result(state=State.OK, summary=f"{len(my_fans)} Fans")
    for key, fan in sorted(my_fans.items()):
        if fan["OperState"] != "operable":
            yield Result(
                state=State.CRIT,
                summary=f"Fan {key.split()[-1][2:]} {fan['OperState']}: average speed {fan.get('SpeedAvg')} RPM",
            )


check_plugin_ucs_bladecenter_fans = CheckPlugin(
    name="ucs_bladecenter_fans",
    service_name="Fans %s",
    discovery_function=discover_ucs_bladecenter_fans,
    check_function=check_ucs_bladecenter_fans,
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


# Fans are grouped per module, usually 8 components
def discover_ucs_bladecenter_fans_temp(section: Section) -> DiscoveryResult:
    for key, values in section.items():
        if "AmbientTemp" in values:
            yield Service(item="Ambient %s FAN" % " ".join(key.split()[:2]))


def _check_ucs_bladecenter_fans_temp(
    item: str,
    params: TempParamDict,
    section: Section,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    sensor_item = item[8:-4]  # drop "Ambient " and " FAN"
    sensor_list: list[TemperatureSensor] = []
    for key, values in section.items():
        if key.startswith(sensor_item) and "AmbientTemp" in values:
            loc = key.split()[-1].split(".")
            temp = float(values["AmbientTemp"])
            sensor = TemperatureSensor(
                id=f"Module {loc[0]} Fan {loc[1]}",
                temp=temp,
                result=check_temperature(temp, params).reading,
            )
            sensor_list.append(sensor)
    yield from aggregate_temperature_results(sensor_list, params, value_store)


def check_ucs_bladecenter_fans_temp(
    item: str, params: TempParamDict, section: Section
) -> CheckResult:
    yield from _check_ucs_bladecenter_fans_temp(item, params, section, get_value_store())


check_plugin_ucs_bladecenter_fans_temp = CheckPlugin(
    name="ucs_bladecenter_fans_temp",
    service_name="Temperature %s",
    sections=["ucs_bladecenter_fans"],
    discovery_function=discover_ucs_bladecenter_fans_temp,
    check_function=check_ucs_bladecenter_fans_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (40.0, 50.0),
    },
)
