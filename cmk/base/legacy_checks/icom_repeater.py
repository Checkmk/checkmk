#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="possibly-undefined"
# mypy: disable-error-code="type-arg"

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import contains, SNMPTree
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

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


def parse_icom_repeater(string_table):
    parsed: dict[str, int | dict | float] = {}
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


def discover_icom_repeater_ps_volt(parsed):
    if "ps_voltage" in parsed:
        yield None, {}


def check_icom_repeater_ps_volt(_no_item, params, parsed):
    return check_levels(
        parsed["ps_voltage"],
        "voltage",
        params["levels_upper"] + params["levels_lower"],
        human_readable_func=lambda x: f"{x:.1f} V",
    )


check_info["icom_repeater.ps_volt"] = LegacyCheckDefinition(
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


def discover_icom_repeater_pll_volt(parsed):
    if "rx_pll_lock_voltage" in parsed:
        yield "RX", {}
    if "tx_pll_lock_voltage" in parsed:
        yield "TX", {}


def check_icom_repeater_pll_volt(item, params, parsed):
    voltage = parsed[item.lower() + "_pll_lock_voltage"]
    freq = parsed["repeater_frequency"][item.lower()]
    paramlist = params.get(item.lower(), None)

    if not paramlist:
        return 1, "Please specify parameters for PLL voltage", [("voltage", voltage)]

    i = 0
    while i < len(paramlist):
        if paramlist[i][0] >= freq:
            warn_lower, crit_lower, warn, crit = paramlist[i - 1][1:]

    infotext = "%.1f V" % voltage
    levelstext = f" (warn/crit below {warn_lower:.1f}/{crit_lower:.1f} V and at or above {warn:.1f}/{crit:.1f} V)"
    if voltage < crit_lower or voltage >= crit:
        status = 2
    elif voltage < warn_lower or voltage >= warn:
        status = 1
    else:
        status = 0
    if status:
        infotext += levelstext

    perfdata = [("voltage", voltage, warn, crit, warn_lower, crit_lower)]

    return status, infotext, perfdata


check_info["icom_repeater.pll_volt"] = LegacyCheckDefinition(
    name="icom_repeater_pll_volt",
    service_name="%s PLL Lock Voltage",
    sections=["icom_repeater"],
    discovery_function=discover_icom_repeater_pll_volt,
    check_function=check_icom_repeater_pll_volt,
    check_ruleset_name="pll_lock_voltage",
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


def discover_icom_repeater_temp(parsed):
    if "temp" in parsed:
        return [("System", {})]
    return []


def check_icom_repeater_temp(_no_item, params, parsed):
    return check_temperature(
        parsed["temp"],
        params,
        "icom_repeater_temp",
        dev_unit=parsed["temp_devunit"],
        dev_status=parsed["temp_devstatus"],
    )


check_info["icom_repeater.temp"] = LegacyCheckDefinition(
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


def discover_icom_repeater(parsed):
    if parsed:
        return [(None, None)]
    return []


def check_icom_repeater(_no_item, _no_params, parsed):
    yield 0, "ESN Number: %s" % parsed["esnno"]

    infotext = "Repeater operation status: %s" % parsed["repop"]
    if parsed["repop"] == "off":
        yield 2, infotext
    elif parsed["repop"] == "on":
        yield 0, infotext
    else:
        yield 3, "Repeater operation status unknown"


check_info["icom_repeater"] = LegacyCheckDefinition(
    name="icom_repeater",
    detect=contains(".1.3.6.1.2.1.1.1.0", "fr5000"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2021.8.1",
        oids=["1", "2", "101"],
    ),
    parse_function=parse_icom_repeater,
    service_name="Repeater Info",
    discovery_function=discover_icom_repeater,
    check_function=check_icom_repeater,
)
