#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v1.type_defs import StringTable
from cmk.agent_based.v2 import CheckResult, DiscoveryResult, get_value_store, Result, Service, State

from .humidity import check_humidity, CheckParams
from .temperature import check_temperature, TempParamDict

#   .--General-------------------------------------------------------------.
#   |                                                  _                   |
#   |                   __ _  ___ _ __   ___ _ __ __ _| |                  |
#   |                  / _` |/ _ \ '_ \ / _ \ '__/ _` | |                  |
#   |                 | (_| |  __/ | | |  __/ | | (_| | |                  |
#   |                  \__, |\___|_| |_|\___|_|  \__,_|_|                  |
#   |                  |___/                                               |
#   +----------------------------------------------------------------------+

# States for sensors with levels as they are defined in SPAGENT-MIB
akcp_sensor_level_states = {
    "1": (2, "no status"),
    "2": (0, "normal"),
    "3": (1, "high warning"),
    "4": (2, "high critical"),
    "5": (1, "low warning"),
    "6": (2, "low critical"),
    "7": (2, "sensor error"),
}

Section = list[list[str]]


def inventory_akcp_sensor_no_params(section: Section) -> DiscoveryResult:
    for line in section:
        # "1" means online, "2" offline
        if line[-1] == "1":
            yield Service(item=line[0])


def parse_akcp_sensor(string_table: StringTable) -> Section:
    return string_table


# .
#   .--Humidity------------------------------------------------------------.
#   |              _                     _     _ _ _                       |
#   |             | |__  _   _ _ __ ___ (_) __| (_) |_ _   _               |
#   |             | '_ \| | | | '_ ` _ \| |/ _` | | __| | | |              |
#   |             | | | | |_| | | | | | | | (_| | | |_| |_| |              |
#   |             |_| |_|\__,_|_| |_| |_|_|\__,_|_|\__|\__, |              |
#   |                                                  |___/               |
#   +----------------------------------------------------------------------+

AKCP_HUMIDITY_CHECK_DEFAULT_PARAMETERS = {
    "levels": (60.0, 65.0),
    "levels_lower": (30.0, 35.0),
}


def inventory_akcp_humidity(section: Section) -> DiscoveryResult:
    for description, _percent, _status, online in section:
        if online == "1":
            yield Service(item=description)


def check_akcp_humidity(item: str, params: CheckParams, section: Section) -> CheckResult:
    for description, percent, status, online in section:
        if description == item:
            # Online is set to "2" if sensor is offline
            if online != "1":
                yield Result(state=State.CRIT, summary="sensor is offline")

            if status in ["1", "7"]:
                state, state_name = akcp_sensor_level_states[status]
                yield Result(state=State(state), summary=f"State: {state_name}")

            if percent:
                yield from check_humidity(int(percent), params)


# .
#   .--Temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+

AKCP_TEMP_CHECK_DEFAULT_PARAMETERS = {
    "levels": (32.0, 35.0),
}


def inventory_akcp_sensor_temp(section: Section) -> DiscoveryResult:
    for line in section:
        # sensorProbeTempOnline or sensorTemperatureGoOffline has to be at last index
        # "1" means online, "2" offline
        if line[-1] == "1":
            yield Service(item=line[0])


def check_akcp_sensor_temp(item: str, params: TempParamDict, section: Section) -> CheckResult:
    for (
        description,
        degree,
        unit,
        status,
        low_crit,
        low_warn,
        high_warn,
        high_crit,
        degreeraw,
        online,
    ) in section:
        if description == item:
            # Online is set to "2" if sensor is offline
            if online != "1":
                yield Result(state=State.CRIT, summary="sensor is offline")

            if status in ["1", "7"]:
                state, state_name = akcp_sensor_level_states[status]
                yield Result(state=State(state), summary=f"State: {state_name}")

            # Unit "F" or "0" stands for Fahrenheit and "C" or "1" for Celsius
            if unit.isdigit():
                unit_normalised = "f" if unit == "0" else "c"
                low_c, low_w, high_w, high_c = list(
                    map(float, (low_crit, low_warn, high_warn, high_crit))
                )
            else:
                unit_normalised = unit.lower()
                if int(high_crit) > 100:
                    # Devices with "F" or "C" have the levels in degrees * 10
                    low_c, low_w, high_w, high_c = (
                        float(t) / 10 for t in (low_crit, low_warn, high_warn, high_crit)
                    )
                else:
                    low_c, low_w, high_w, high_c = (
                        float(t) for t in (low_crit, low_warn, high_warn, high_crit)
                    )

            if degreeraw and degreeraw != "0":
                temperature = float(degreeraw) / 10.0
            elif not degree:
                yield Result(state=State.UNKNOWN, summary="Temperature information not found")
                return
            else:
                temperature = float(degree)

            yield from check_temperature(
                reading=temperature,
                params=params,
                unique_name=f"akcp_sensor_temp_{item}",
                value_store=get_value_store(),
                dev_unit=unit_normalised,
                dev_levels=(high_w, high_c),
                dev_levels_lower=(low_w, low_c),
            )


# .
#   .--Water & Smoke-------------------------------------------------------.
#   |               _               ___                         _          |
#   |__      ____ _| |_ ___ _ __   ( _ )    ___ _ __ ___   ___ | | _____   |
#   |\ \ /\ / / _` | __/ _ \ '__|  / _ \/\ / __| '_ ` _ \ / _ \| |/ / _ \  |
#   | \ V  V / (_| | ||  __/ |    | (_>  < \__ \ | | | | | (_) |   <  __/  |
#   |  \_/\_/ \__,_|\__\___|_|     \___/\/ |___/_| |_| |_|\___/|_|\_\___|  |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def check_akcp_sensor_relay(item: str, section: Section) -> CheckResult:
    # States for sensors with relays as they are defined in SPAGENT-MIB
    relay_states = {
        "1": (2, "no status"),
        "2": (0, "normal"),
        "4": (2, "high critical"),
        "6": (2, "low critical"),
        "7": (2, "sensor error"),
        "8": (2, "relay on"),
        "9": (0, "relay off"),
    }

    for description, status, online in section:
        if description == item:
            # Online is set to "2" if sensor is offline
            if online != "1":
                yield Result(state=State.CRIT, summary="sensor is offline")

            state, state_name = relay_states[status]
            yield Result(state=State(state), summary=f"State: {state_name}")


# .
#   .--Drycontact----------------------------------------------------------.
#   |             _                            _             _             |
#   |          __| |_ __ _   _  ___ ___  _ __ | |_ __ _  ___| |_           |
#   |         / _` | '__| | | |/ __/ _ \| '_ \| __/ _` |/ __| __|          |
#   |        | (_| | |  | |_| | (_| (_) | | | | || (_| | (__| |_           |
#   |         \__,_|_|   \__, |\___\___/|_| |_|\__\__,_|\___|\__|          |
#   |                    |___/                                             |
#   +----------------------------------------------------------------------+


def check_akcp_sensor_drycontact(item: str, section: Section) -> CheckResult:
    # States which are not configurable by user as they are defined in SPAGENT-MIB
    states = {
        "1": (2, "no status"),
        "7": (2, "sensor error"),
        "8": (2, "output low"),
        "9": (2, "output high"),
    }

    for line in section:
        if item == line[0]:
            if len(line) == 5:
                status, crit_desc, normal_desc, online = line[1:]
            else:
                status, online = line[1:]
                normal_desc = "Drycontact OK"
                crit_desc = "Drycontact on Error"

            if online != "1":
                infotext = "Sensor is offline"
                state = 2
            elif status == "2":
                state = 0
                infotext = normal_desc
            elif status in ["4", "6"]:
                state = 2
                infotext = crit_desc
            else:
                state, infotext = states[status]

            yield Result(state=State(state), summary=infotext)
