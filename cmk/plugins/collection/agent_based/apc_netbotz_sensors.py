#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)
from cmk.plugins.lib.humidity import check_humidity
from cmk.plugins.lib.temperature import check_temperature, TempParamType

# .1.3.6.1.4.1.5528.100.4.1.1.1.1.636159851 nbAlinkEnc_0_4_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.882181375 nbAlinkEnc_2_1_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.1619732064 nbAlinkEnc_0_2_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.1665932156 nbAlinkEnc_1_4_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.1751899818 nbAlinkEnc_2_2_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.1857547767 nbAlinkEnc_1_5_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.2370211927 nbAlinkEnc_1_6_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.2618588815 nbAlinkEnc_2_3_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.2628357572 nbAlinkEnc_0_1_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.3031356659 nbAlinkEnc_0_5_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.3056253200 nbAlinkEnc_0_6_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.3103062985 nbAlinkEnc_2_4_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.3328914949 nbAlinkEnc_1_3_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.1.3406802758 nbAlinkEnc_0_3_TEMP
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.636159851 252
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.882181375 222
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.1619732064 222
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.1665932156 216
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.1751899818 245
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.1857547767 234
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.2370211927 240
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.2618588815 220
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.2628357572 229
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.3031356659 0
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.3056253200 0
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.3103062985 215
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.3328914949 234
# .1.3.6.1.4.1.5528.100.4.1.1.1.2.3406802758 238
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.636159851 25.200000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.882181375 22.200000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.1619732064 22.200000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.1665932156 21.600000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.1751899818 24.500000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.1857547767 23.400000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.2370211927 24.000000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.2618588815 22.000000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.2628357572 22.900000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.3031356659
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.3056253200
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.3103062985 21.500000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.3328914949 23.400000
# .1.3.6.1.4.1.5528.100.4.1.1.1.7.3406802758 23.800000

# .1.3.6.1.4.1.5528.100.4.1.2.1.1.421607638 nbAlinkEnc_1_5_HUMI
# .1.3.6.1.4.1.5528.100.4.1.2.1.1.581338442 nbAlinkEnc_1_3_HUMI
# .1.3.6.1.4.1.5528.100.4.1.2.1.1.1121716336 nbAlinkEnc_0_6_HUMI
# .1.3.6.1.4.1.5528.100.4.1.2.1.1.3273299739 nbAlinkEnc_0_3_HUMI
# .1.3.6.1.4.1.5528.100.4.1.2.1.1.4181308384 nbAlinkEnc_0_5_HUMI
# .1.3.6.1.4.1.5528.100.4.1.2.1.2.421607638 370
# .1.3.6.1.4.1.5528.100.4.1.2.1.2.581338442 320
# .1.3.6.1.4.1.5528.100.4.1.2.1.2.1121716336 0
# .1.3.6.1.4.1.5528.100.4.1.2.1.2.3273299739 320
# .1.3.6.1.4.1.5528.100.4.1.2.1.2.4181308384 0
# .1.3.6.1.4.1.5528.100.4.1.2.1.7.421607638 37.000000
# .1.3.6.1.4.1.5528.100.4.1.2.1.7.581338442 32.000000
# .1.3.6.1.4.1.5528.100.4.1.2.1.7.1121716336
# .1.3.6.1.4.1.5528.100.4.1.2.1.7.3273299739 32.000000
# .1.3.6.1.4.1.5528.100.4.1.2.1.7.4181308384

# .1.3.6.1.4.1.5528.100.4.1.3.1.1.1000015730 nbAlinkEnc_0_5_DWPT
# .1.3.6.1.4.1.5528.100.4.1.3.1.1.1490079962 nbAlinkEnc_0_3_DWPT
# .1.3.6.1.4.1.5528.100.4.1.3.1.1.2228353183 nbAlinkEnc_0_6_DWPT
# .1.3.6.1.4.1.5528.100.4.1.3.1.1.2428087247 nbAlinkEnc_1_3_DWPT
# .1.3.6.1.4.1.5528.100.4.1.3.1.1.3329736831 nbAlinkEnc_1_5_DWPT
# .1.3.6.1.4.1.5528.100.4.1.3.1.2.1000015730 0
# .1.3.6.1.4.1.5528.100.4.1.3.1.2.1490079962 61
# .1.3.6.1.4.1.5528.100.4.1.3.1.2.2228353183 0
# .1.3.6.1.4.1.5528.100.4.1.3.1.2.2428087247 57
# .1.3.6.1.4.1.5528.100.4.1.3.1.2.3329736831 78
# .1.3.6.1.4.1.5528.100.4.1.3.1.7.1000015730
# .1.3.6.1.4.1.5528.100.4.1.3.1.7.1490079962 6.100000
# .1.3.6.1.4.1.5528.100.4.1.3.1.7.2228353183
# .1.3.6.1.4.1.5528.100.4.1.3.1.7.2428087247 5.700000
# .1.3.6.1.4.1.5528.100.4.1.3.1.7.3329736831 7.800000


@dataclass(frozen=True)
class SensorData:
    reading: float
    label: str


Section = Mapping[str, Mapping[str, SensorData]]


def parse_apc_netbotz_sensors(
    string_table: Sequence[StringTable], parse_reading: Callable[[str], float]
) -> Section:
    parsed: dict[str, dict[str, SensorData]] = {}
    for item_type, block in zip(("temp", "humidity", "dewpoint"), string_table):
        for item_name, reading_str, label, plugged_in_state in block:
            if not plugged_in_state:
                continue
            parsed.setdefault(item_type, {}).setdefault(
                item_name, SensorData(reading=parse_reading(reading_str), label=label)
            )
    return parsed


def discover_apc_netbotz_sensors(section: Section, sensor_type: str) -> DiscoveryResult:
    for item in section.get(sensor_type, []):
        yield Service(item=item)


def check_apc_netbotz_sensors(
    item: str, params: TempParamType, section: Section, sensor_type: str
) -> CheckResult:
    if item in section.get(sensor_type, []):
        data = section[sensor_type][item]
        yield Result(state=State.OK, summary=f"[{data.label}]")
        yield from check_temperature(
            data.reading,
            params,
            unique_name=f"apc_netbotz_sensors_{sensor_type}_{item}",
            value_store=get_value_store(),
        )


# ACP Netbotz v2 sensors deliver sensor readings in tenth of a degree or tenth of a percent
def parse_apc_netbotz_v2_sensors(string_table: Sequence[StringTable]) -> Section:
    def parse_reading(reading: str) -> float:
        return float(reading) / 10.0

    return parse_apc_netbotz_sensors(string_table, parse_reading)


snmp_section_apc_netbotz_v2_sensors = SNMPSection(
    name="apc_netbotz_v2_sensors",
    parse_function=parse_apc_netbotz_v2_sensors,
    parsed_section_name="apc_netbotz_sensors",
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.5528.100.4.1.1.1",
            oids=["1", "2", "4", "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.5528.100.4.1.2.1",
            oids=["1", "2", "4", "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.5528.100.4.1.3.1",
            oids=["1", "2", "4", "7"],
        ),
    ],
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.5528.100.20.10"),
)


# ACP Netbotz 50 sensors deliver sensor readings in degrees or percent
def parse_apc_netbotz_50_sensors(string_table: Sequence[StringTable]) -> Section:
    return parse_apc_netbotz_sensors(string_table, float)


snmp_section_apc_netbotz_50_sensors = SNMPSection(
    name="apc_netbotz_50_sensors",
    parse_function=parse_apc_netbotz_50_sensors,
    parsed_section_name="apc_netbotz_sensors",
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.52674.500.4.1.1.1",
            oids=["1", "2", "4", "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.52674.500.4.1.2.1",
            oids=["1", "2", "4", "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.52674.500.4.1.3.1",
            oids=["1", "2", "4", "7"],
        ),
    ],
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.52674.500"),
)

#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'


def discover_apc_netbotz_sensors_temp(section: Section) -> DiscoveryResult:
    yield from discover_apc_netbotz_sensors(section, "temp")


def check_apc_netbotz_sensors_temp(
    item: str, params: TempParamType, section: Section
) -> CheckResult:
    yield from check_apc_netbotz_sensors(item, params, section, "temp")


check_plugin_apc_netbotz_sensors = CheckPlugin(
    name="apc_netbotz_sensors",
    sections=["apc_netbotz_sensors"],
    service_name="Temperature %s",
    discovery_function=discover_apc_netbotz_sensors_temp,
    check_function=check_apc_netbotz_sensors_temp,
    check_ruleset_name="temperature",
    check_default_parameters={  # suggested by customer
        "levels": (30.0, 35.0),
        "levels_lower": (25.0, 20.0),
    },
)


# .
#   .--dewpoint------------------------------------------------------------.
#   |                 _                           _       _                |
#   |              __| | _____      ___ __   ___ (_)_ __ | |_              |
#   |             / _` |/ _ \ \ /\ / / '_ \ / _ \| | '_ \| __|             |
#   |            | (_| |  __/\ V  V /| |_) | (_) | | | | | |_              |
#   |             \__,_|\___| \_/\_/ | .__/ \___/|_|_| |_|\__|             |
#   |                                |_|                                   |
#   '----------------------------------------------------------------------'


def discover_apc_netbotz_sensors_dewpoint(section: Section) -> DiscoveryResult:
    yield from discover_apc_netbotz_sensors(section, "dewpoint")


def check_apc_netbotz_sensors_dewpoint(
    item: str, params: TempParamType, section: Section
) -> CheckResult:
    yield from check_apc_netbotz_sensors(item, params, section, "dewpoint")


check_plugin_apc_netbotz_sensors_dewpoint = CheckPlugin(
    name="apc_netbotz_sensors_dewpoint",
    sections=["apc_netbotz_sensors"],
    service_name="Dew point %s",
    discovery_function=discover_apc_netbotz_sensors_dewpoint,
    check_function=check_apc_netbotz_sensors_dewpoint,
    check_ruleset_name="temperature",
    check_default_parameters={  # suggested by customer
        "levels": (18.0, 25.0),
        "levels_lower": (-4.0, -6.0),
    },
)

# .
#   .--humidity------------------------------------------------------------.
#   |              _                     _     _ _ _                       |
#   |             | |__  _   _ _ __ ___ (_) __| (_) |_ _   _               |
#   |             | '_ \| | | | '_ ` _ \| |/ _` | | __| | | |              |
#   |             | | | | |_| | | | | | | | (_| | | |_| |_| |              |
#   |             |_| |_|\__,_|_| |_| |_|_|\__,_|_|\__|\__, |              |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'


def discover_apc_netbotz_sensors_humidity(section: Section) -> DiscoveryResult:
    yield from discover_apc_netbotz_sensors(section, "humidity")


def check_apc_netbotz_sensors_humidity(
    item: str, params: Mapping[str, object], section: Section
) -> CheckResult:
    if item in section.get("humidity", []):
        data = section["humidity"][item]
        yield Result(state=State.OK, summary=f"[{data.label}]")
        yield from check_humidity(data.reading, params)


check_plugin_apc_netbotz_sensors_humidity = CheckPlugin(
    name="apc_netbotz_sensors_humidity",
    sections=["apc_netbotz_sensors"],
    service_name="Humidity %s",
    discovery_function=discover_apc_netbotz_sensors_humidity,
    check_function=check_apc_netbotz_sensors_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={  # suggested by customer
        "levels": (60.0, 65.0),
        "levels_lower": (35.0, 30.0),
    },
)
