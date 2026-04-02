#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer untile we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
)
from cmk.legacy_includes.temperature import check_temperature

#   .--Parse function------------------------------------------------------.
#   |  ____                        __                  _   _               |
#   | |  _ \ __ _ _ __ ___  ___   / _|_   _ _ __   ___| |_(_) ___  _ __    |
#   | | |_) / _` | '__/ __|/ _ \ | |_| | | | '_ \ / __| __| |/ _ \| '_ \   |
#   | |  __/ (_| | |  \__ \  __/ |  _| |_| | | | | (__| |_| | (_) | | | |  |
#   | |_|   \__,_|_|  |___/\___| |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def parse_icom_repeater(string_table: list[list[str]]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for line in string_table:
        if line[1] == "Temperature":
            parsed["temp"] = float(line[2][:-1])
            parsed["temp_devunit"] = line[2][-1].lower()

        elif line[1] == "ESN number":
            parsed["esnno"] = line[2]

        elif line[1] == "Repeater operation":
            parsed["repop"] = line[2].lower()

        elif line[1] == "Abnormal temperature detection":
            if line[2] == "Not detected":
                parsed["temp_devstatus"] = 0
            else:
                parsed["temp_devstatus"] = 2

        elif line[1] == "Power-supply voltage":
            parsed["ps_voltage"] = float(line[2][:-1])

        elif line[1] == "Abnormal power-supply voltage detection":
            if line[2] == "Not detected":
                parsed["ps_volt_devstatus"] = 0
            else:
                parsed["ps_volt_devstatus"] = 2

        elif line[1] == "TX PLL lock voltage":
            try:
                parsed["tx_pll_lock_voltage"] = float(line[2][:-1])
            except Exception:
                pass

        elif line[1] == "RX PLL lock voltage":
            try:
                parsed["rx_pll_lock_voltage"] = float(line[2][:-1])
            except Exception:
                pass

        elif line[1] == "Repeater frequency":
            parsed["repeater_frequency"] = {
                b.split(":")[0].lower(): int(b.split(":")[1])
                for b in [a.lstrip() for a in line[2].split(",")]
            }

    return parsed


# .
#   .--Power Supply Voltage------------------------------------------------.
#   |    ____                          ____                    _           |
#   |   |  _ \ _____      _____ _ __  / ___| _   _ _ __  _ __ | |_   _     |
#   |   | |_) / _ \ \ /\ / / _ \ '__| \___ \| | | | '_ \| '_ \| | | | |    |
#   |   |  __/ (_) \ V  V /  __/ |     ___) | |_| | |_) | |_) | | |_| |    |
#   |   |_|   \___/ \_/\_/ \___|_|    |____/ \__,_| .__/| .__/|_|\__, |    |
#   |                                             |_|   |_|      |___/     |
#   |                 __     __    _ _                                     |
#   |                 \ \   / /__ | | |_ __ _  __ _  ___                   |
#   |                  \ \ / / _ \| | __/ _` |/ _` |/ _ \                  |
#   |                   \ V / (_) | | || (_| | (_| |  __/                  |
#   |                    \_/ \___/|_|\__\__,_|\__, |\___|                  |
#   |                                         |___/                        |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_icom_repeater_ps_volt(section: Any) -> DiscoveryResult:
    if "ps_voltage" in section:
        yield Service()


def check_icom_repeater_ps_volt(params: Mapping[str, Any], section: Any) -> CheckResult:
    yield from check_levels(
        section["ps_voltage"],
        "voltage",
        params["levels_upper"] + params["levels_lower"],
        human_readable_func=lambda x: f"{x:.1f} V",
    )


check_plugin_icom_repeater_ps_volt = CheckPlugin(
    name="icom_repeater_ps_volt",
    service_name="Power Supply Voltage",
    sections=["icom_repeater"],
    discovery_function=discover_icom_repeater_ps_volt,
    check_function=check_icom_repeater_ps_volt,
    check_ruleset_name="ps_voltage",
    check_default_parameters={
        "levels_lower": (13.5, 13.2),
        "levels_upper": (14.1, 14.4),
    },
)

# .
#   .--PLL Voltage---------------------------------------------------------.
#   |        ____  _     _      __     __    _ _                           |
#   |       |  _ \| |   | |     \ \   / /__ | | |_ __ _  __ _  ___         |
#   |       | |_) | |   | |      \ \ / / _ \| | __/ _` |/ _` |/ _ \        |
#   |       |  __/| |___| |___    \ V / (_) | | || (_| | (_| |  __/        |
#   |       |_|   |_____|_____|    \_/ \___/|_|\__\__,_|\__, |\___|        |
#   |                                                   |___/              |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_icom_repeater_pll_volt(section: Any) -> DiscoveryResult:
    if "rx_pll_lock_voltage" in section:
        yield Service(item="RX")
    if "tx_pll_lock_voltage" in section:
        yield Service(item="TX")


def check_icom_repeater_pll_volt(item: str, params: Mapping[str, Any], section: Any) -> CheckResult:
    voltage = section[item.lower() + "_pll_lock_voltage"]
    freq = section["repeater_frequency"][item.lower()]
    paramlist = params.get(item.lower(), None)

    if not paramlist:
        yield Result(state=State.WARN, summary="Please specify parameters for PLL voltage")
        yield Metric("voltage", voltage)
        return

    i = 0
    while i < len(paramlist):
        if paramlist[i][0] >= freq:
            warn_lower, crit_lower, warn, crit = paramlist[i - 1][1:]

    infotext = "%.1f V" % voltage
    levelstext = f" (warn/crit below {warn_lower:.1f}/{crit_lower:.1f} V and at or above {warn:.1f}/{crit:.1f} V)"  # type: ignore[possibly-undefined]  # pre-existing bug
    if voltage < crit_lower or voltage >= crit:
        status = 2
    elif voltage < warn_lower or voltage >= warn:
        status = 1
    else:
        status = 0
    if status:
        infotext += levelstext

    yield Result(state=State(status), summary=infotext)
    yield Metric("voltage", voltage, levels=(warn, crit))
    return


check_plugin_icom_repeater_pll_volt = CheckPlugin(
    name="icom_repeater_pll_volt",
    service_name="%s PLL Lock Voltage",
    sections=["icom_repeater"],
    discovery_function=discover_icom_repeater_pll_volt,
    check_function=check_icom_repeater_pll_volt,
    check_ruleset_name="pll_lock_voltage",
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
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_icom_repeater_temp(section: Any) -> DiscoveryResult:
    if "temp" in section:
        yield Service(item="System")


def check_icom_repeater_temp(item: str, params: Mapping[str, Any], section: Any) -> CheckResult:
    yield from check_temperature(  # type: ignore[misc]
        section["temp"],
        params,  # type: ignore[arg-type]
        "icom_repeater_temp",
        dev_unit=section["temp_devunit"],
        dev_status=section["temp_devstatus"],
    )


check_plugin_icom_repeater_temp = CheckPlugin(
    name="icom_repeater_temp",
    service_name="Temperature %s",
    sections=["icom_repeater"],
    discovery_function=discover_icom_repeater_temp,
    check_function=check_icom_repeater_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (50.0, 55.0),
        "levels_lower": (-20.0, -25.0),
    },
)

# .
#   .--Repeater Info-------------------------------------------------------.
#   |    ____                       _              ___        __           |
#   |   |  _ \ ___ _ __   ___  __ _| |_ ___ _ __  |_ _|_ __  / _| ___      |
#   |   | |_) / _ \ '_ \ / _ \/ _` | __/ _ \ '__|  | || '_ \| |_ / _ \     |
#   |   |  _ <  __/ |_) |  __/ (_| | ||  __/ |     | || | | |  _| (_) |    |
#   |   |_| \_\___| .__/ \___|\__,_|\__\___|_|    |___|_| |_|_|  \___/     |
#   |             |_|                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_icom_repeater(section: Any) -> DiscoveryResult:
    if section:
        yield Service()


def check_icom_repeater(section: Any) -> CheckResult:
    yield Result(state=State.OK, summary="ESN Number: %s" % section["esnno"])

    infotext = "Repeater operation status: %s" % section["repop"]
    if section["repop"] == "off":
        yield Result(state=State.CRIT, summary=infotext)
    elif section["repop"] == "on":
        yield Result(state=State.OK, summary=infotext)
    else:
        yield Result(state=State.UNKNOWN, summary="Repeater operation status unknown")


snmp_section_icom_repeater = SimpleSNMPSection(
    name="icom_repeater",
    detect=contains(".1.3.6.1.2.1.1.1.0", "fr5000"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2021.8.1",
        oids=["1", "2", "101"],
    ),
    parse_function=parse_icom_repeater,
)


check_plugin_icom_repeater = CheckPlugin(
    name="icom_repeater",
    service_name="Repeater Info",
    discovery_function=discover_icom_repeater,
    check_function=check_icom_repeater,
)
