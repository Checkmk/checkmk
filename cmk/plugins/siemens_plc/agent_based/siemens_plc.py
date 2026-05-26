#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType

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


agent_section_siemens_plc = AgentSection(
    name="siemens_plc",
    parse_function=parse_siemens_plc,
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


def discover_siemens_plc_temp(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[1] == "temp":
            yield Service(item=f"{line[0]} {line[2]}")


def check_siemens_plc_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    for line in section:
        if line[1] == "temp" and f"{line[0]} {line[2]}" == item:
            temp = float(line[-1])
            yield from check_temperature(
                temp,
                params,
                unique_name=f"siemens_plc_{item}",
                value_store=get_value_store(),
            )
            return


check_plugin_siemens_plc_temp = CheckPlugin(
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


def discover_siemens_plc_flag(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[1] == "flag":
            yield Service(item=f"{line[0]} {line[2]}")


def check_siemens_plc_flag(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    expected_state = params["expected_state"]
    for line in section:
        if line[1] == "flag" and f"{line[0]} {line[2]}" == item:
            flag_state = line[-1] == "True"
            if flag_state:
                yield Result(
                    state=State.OK if expected_state else State.CRIT,
                    summary="On",
                )
                return

            yield Result(
                state=State.CRIT if expected_state else State.OK,
                summary="Off",
            )
            return


check_plugin_siemens_plc_flag = CheckPlugin(
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


def discover_siemens_plc_duration(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[1].startswith("hours") or line[1].startswith("seconds"):
            yield Service(item=f"{line[0]} {line[2]}")


def check_siemens_plc_duration(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    for line in section:
        if (
            line[1].startswith("hours") or line[1].startswith("seconds")
        ) and f"{line[0]} {line[2]}" == item:
            value_store = get_value_store()
            if line[1].startswith("hours"):
                seconds = float(line[-1]) * 3600
            else:
                seconds = float(line[-1])

            key = f"siemens_plc.duration.{item}"
            old_seconds = value_store.get(key)
            if old_seconds is not None and old_seconds > seconds:
                yield Result(
                    state=State.CRIT,
                    summary=f"Reduced from {render.time_offset(old_seconds)} to {render.time_offset(seconds)}",
                )
                yield Metric(line[1], seconds)
                return

            value_store[key] = seconds

            state = State.OK
            warn, crit = params.get("duration", (None, None))
            if crit is not None and seconds >= crit:
                state = State.CRIT
            elif warn is not None and seconds >= warn:
                state = State.WARN

            yield Result(state=state, summary=render.time_offset(seconds))
            yield Metric(line[1], seconds)
            return


check_plugin_siemens_plc_duration = CheckPlugin(
    name="siemens_plc_duration",
    service_name="Duration %s",
    sections=["siemens_plc"],
    discovery_function=discover_siemens_plc_duration,
    check_function=check_siemens_plc_duration,
    check_ruleset_name="siemens_plc_duration",
    check_default_parameters={},
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


def discover_siemens_plc_counter(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[1].startswith("counter"):
            yield Service(item=f"{line[0]} {line[2]}")


def check_siemens_plc_counter(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    for line in section:
        if line[1].startswith("counter") and f"{line[0]} {line[2]}" == item:
            value_store = get_value_store()
            value = int(line[-1])

            key = f"siemens_plc.counter.{item}"
            old_value = value_store.get(key)
            if old_value is not None and old_value > value:
                yield Result(state=State.CRIT, summary=f"Reduced from {old_value} to {value}")
                yield Metric(line[1], float(value))
                return
            value_store[key] = value

            state = State.OK
            warn, crit = params.get("levels", (None, None))
            if crit is not None and value >= crit:
                state = State.CRIT
            elif warn is not None and value >= warn:
                state = State.WARN

            yield Result(state=state, summary=str(value))
            yield Metric(line[1], float(value))
            return


check_plugin_siemens_plc_counter = CheckPlugin(
    name="siemens_plc_counter",
    service_name="Counter %s",
    sections=["siemens_plc"],
    discovery_function=discover_siemens_plc_counter,
    check_function=check_siemens_plc_counter,
    check_ruleset_name="siemens_plc_counter",
    check_default_parameters={},
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


def discover_siemens_plc_info(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[1] == "text":
            yield Service(item=f"{line[0]} {line[2]}")


def check_siemens_plc_info(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if line[1] == "text" and f"{line[0]} {line[2]}" == item:
            yield Result(state=State.OK, summary=line[-1])
            return


check_plugin_siemens_plc_info = CheckPlugin(
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


def discover_siemens_plc_cpu_state(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_siemens_plc_cpu_state(section: StringTable) -> CheckResult:
    try:
        state = section[0][0]
    except IndexError:
        return

    if state == "S7CpuStatusRun":
        yield Result(state=State.OK, summary="CPU is running")
        return
    if state == "S7CpuStatusStop":
        yield Result(state=State.CRIT, summary="CPU is stopped")
        return
    yield Result(state=State.UNKNOWN, summary="CPU is in unknown state")


def parse_siemens_plc_cpu_state(string_table: StringTable) -> StringTable:
    return string_table


agent_section_siemens_plc_cpu_state = AgentSection(
    name="siemens_plc_cpu_state",
    parse_function=parse_siemens_plc_cpu_state,
)


check_plugin_siemens_plc_cpu_state = CheckPlugin(
    name="siemens_plc_cpu_state",
    service_name="CPU state",
    discovery_function=discover_siemens_plc_cpu_state,
    check_function=check_siemens_plc_cpu_state,
)
