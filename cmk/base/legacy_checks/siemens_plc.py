#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import get_value_store, render, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

# <<<siemens_plc>>>
# PFT01 temp Gesamt 279183569715
# PFT01 flag Testbit True
# PFT01 flag Testbit2 False
# RGB01 temp Gesamt 123
# RGB01 seconds Fahren 56
# RGB01 seconds Hub 48
# RGB01 seconds LAM1 13
# RGB01 temp Extern 18.7000007629
# RGB01 temp RBG_SCH1 0.0
# RGB01 temp RBG_SCH2 0.0
# RGB01 counter Fahren 31450
# RGB01 counter Hub 8100
# RGB01 counter LAM 5002
# RGB01 counter Lastzyklen 78
# RGB01 counter LAM1_Zyklen 115
# RGB01 seconds Service 109
# RGB01 seconds Serviceintervall 700
# RGB01 text Testtext HRL01-0001-0010-02-07


def parse_siemens_plc(string_table: StringTable) -> StringTable:
    return string_table


check_info["siemens_plc"] = LegacyCheckDefinition(
    name="siemens_plc", parse_function=parse_siemens_plc
)


# .
#   .--Temperature---------------------------------------------------------.
#   |     _____                                   _                        |
#   |    |_   _|__ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |      | |/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |      | |  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      |_|\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_siemens_plc_temp(info):
    return [(l[0] + " " + l[2], {}) for l in info if l[1] == "temp"]


def check_siemens_plc_temp(item, params, info):
    for line in info:
        if line[1] == "temp" and line[0] + " " + line[2] == item:
            temp = float(line[-1])
            return check_temperature(temp, params, "siemens_plc_%s" % item)
    return None


check_info["siemens_plc.temp"] = LegacyCheckDefinition(
    name="siemens_plc_temp",
    service_name="Temperature %s",
    sections=["siemens_plc"],
    discovery_function=discover_siemens_plc_temp,
    check_function=check_siemens_plc_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (70.0, 80.0),
        "device_levels_handling": "devdefault",
    },
)

# .
#   .--State flags---------------------------------------------------------.
#   |           ____  _        _          __ _                             |
#   |          / ___|| |_ __ _| |_ ___   / _| | __ _  __ _ ___             |
#   |          \___ \| __/ _` | __/ _ \ | |_| |/ _` |/ _` / __|            |
#   |           ___) | || (_| | ||  __/ |  _| | (_| | (_| \__ \            |
#   |          |____/ \__\__,_|\__\___| |_| |_|\__,_|\__, |___/            |
#   |                                                |___/                 |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_siemens_plc_flag(info):
    return [(l[0] + " " + l[2], {}) for l in info if l[1] == "flag"]


def check_siemens_plc_flag(item, params, info):
    expected_state = params["expected_state"]
    for line in info:
        if line[1] == "flag" and line[0] + " " + line[2] == item:
            flag_state = line[-1] == "True"
            if flag_state:
                state = 0 if expected_state else 2
                return state, "On"

            state = 2 if expected_state else 0
            return state, "Off"
    return None


check_info["siemens_plc.flag"] = LegacyCheckDefinition(
    name="siemens_plc_flag",
    service_name="Flag %s",
    sections=["siemens_plc"],
    discovery_function=discover_siemens_plc_flag,
    check_function=check_siemens_plc_flag,
    check_ruleset_name="siemens_plc_flag",
    check_default_parameters={"expected_state": False},
)

# .
#   .--Duration------------------------------------------------------------.
#   |               ____                  _   _                            |
#   |              |  _ \ _   _ _ __ __ _| |_(_) ___  _ __                 |
#   |              | | | | | | | '__/ _` | __| |/ _ \| '_ \                |
#   |              | |_| | |_| | | | (_| | |_| | (_) | | | |               |
#   |              |____/ \__,_|_|  \__,_|\__|_|\___/|_| |_|               |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_siemens_plc_duration(info):
    return [
        (l[0] + " " + l[2], {})
        for l in info
        if l[1].startswith("hours") or l[1].startswith("seconds")
    ]


def check_siemens_plc_duration(item, params, info):
    for line in info:
        if (line[1].startswith("hours") or line[1].startswith("seconds")) and line[0] + " " + line[
            2
        ] == item:
            value_store = get_value_store()
            if line[1].startswith("hours"):
                seconds = float(line[-1]) * 3600
            else:
                seconds = float(line[-1])

            perfdata = [(line[1], seconds)]

            key = "siemens_plc.duration.%s" % item
            old_seconds = value_store.get(key)
            if old_seconds is not None and old_seconds > seconds:
                return (
                    2,
                    f"Reduced from {render.time_offset(old_seconds)} to {render.time_offset(seconds)}",
                    perfdata,
                )

            value_store[key] = seconds

            state = 0
            warn, crit = params.get("duration", (None, None))
            if crit is not None and seconds >= crit:
                state = 2
            elif warn is not None and seconds >= warn:
                state = 1

            return state, render.time_offset(seconds), perfdata
    return None


check_info["siemens_plc.duration"] = LegacyCheckDefinition(
    name="siemens_plc_duration",
    service_name="Duration %s",
    sections=["siemens_plc"],
    discovery_function=discover_siemens_plc_duration,
    check_function=check_siemens_plc_duration,
    check_ruleset_name="siemens_plc_duration",
)

# .
#   .--Counter-------------------------------------------------------------.
#   |                  ____                  _                             |
#   |                 / ___|___  _   _ _ __ | |_ ___ _ __                  |
#   |                | |   / _ \| | | | '_ \| __/ _ \ '__|                 |
#   |                | |__| (_) | |_| | | | | ||  __/ |                    |
#   |                 \____\___/ \__,_|_| |_|\__\___|_|                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_siemens_plc_counter(info):
    return [(l[0] + " " + l[2], {}) for l in info if l[1].startswith("counter")]


def check_siemens_plc_counter(item, params, info):
    for line in info:
        if line[1].startswith("counter") and line[0] + " " + line[2] == item:
            value_store = get_value_store()
            value = int(line[-1])
            perfdata = [(line[1], value)]

            key = "siemens_plc.counter.%s" % item
            old_value = value_store.get(key)
            if old_value is not None and old_value > value:
                return 2, f"Reduced from {old_value} to {value}", perfdata
            value_store[key] = value

            state = 0
            warn, crit = params.get("levels", (None, None))
            if crit is not None and value >= crit:
                state = 2
            elif warn is not None and value >= warn:
                state = 1

            return state, "%d" % value, perfdata
    return None


check_info["siemens_plc.counter"] = LegacyCheckDefinition(
    name="siemens_plc_counter",
    service_name="Counter %s",
    sections=["siemens_plc"],
    discovery_function=discover_siemens_plc_counter,
    check_function=check_siemens_plc_counter,
    check_ruleset_name="siemens_plc_counter",
)

# .
#   .--Info----------------------------------------------------------------.
#   |                         ___        __                                |
#   |                        |_ _|_ __  / _| ___                           |
#   |                         | || '_ \| |_ / _ \                          |
#   |                         | || | | |  _| (_) |                         |
#   |                        |___|_| |_|_|  \___/                          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_siemens_plc_info(info):
    return [(l[0] + " " + l[2], {}) for l in info if l[1] == "text"]


def check_siemens_plc_info(item, _no_params, info):
    for line in info:
        if line[1] == "text" and line[0] + " " + line[2] == item:
            return 0, line[-1]
    return None


check_info["siemens_plc.info"] = LegacyCheckDefinition(
    name="siemens_plc_info",
    service_name="Info %s",
    sections=["siemens_plc"],
    discovery_function=discover_siemens_plc_info,
    check_function=check_siemens_plc_info,
)

# .
#   .--CPU-State-----------------------------------------------------------.
#   |             ____ ____  _   _      ____  _        _                   |
#   |            / ___|  _ \| | | |    / ___|| |_ __ _| |_ ___             |
#   |           | |   | |_) | | | |____\___ \| __/ _` | __/ _ \            |
#   |           | |___|  __/| |_| |_____|__) | || (_| | ||  __/            |
#   |            \____|_|    \___/     |____/ \__\__,_|\__\___|            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_siemens_plc_cpu_state(info):
    return [(None, None)]


def check_siemens_plc_cpu_state(_no_item, _no_params, info):
    try:
        state = info[0][0]
    except IndexError:
        return None

    if state == "S7CpuStatusRun":
        return 0, "CPU is running"
    if state == "S7CpuStatusStop":
        return 2, "CPU is stopped"
    return 3, "CPU is in unknown state"


def parse_siemens_plc_cpu_state(string_table: StringTable) -> StringTable:
    return string_table


check_info["siemens_plc_cpu_state"] = LegacyCheckDefinition(
    name="siemens_plc_cpu_state",
    parse_function=parse_siemens_plc_cpu_state,
    service_name="CPU state",
    discovery_function=discover_siemens_plc_cpu_state,
    check_function=check_siemens_plc_cpu_state,
)
