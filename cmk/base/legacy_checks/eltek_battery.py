#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.eltek.lib import DETECT_ELTEK

check_info = {}

# .1.3.6.1.4.1.12148.9.3.1.0 --> ELTEK-DISTRIBUTED-MIB::batteryName.0
# .1.3.6.1.4.1.12148.9.3.2.0 5485 --> ELTEK-DISTRIBUTED-MIB::batteryVoltage.0
# .1.3.6.1.4.1.12148.9.3.3.0 0 --> ELTEK-DISTRIBUTED-MIB::batteryCurrent.0
# .1.3.6.1.4.1.12148.9.3.4.0 19 --> ELTEK-DISTRIBUTED-MIB::batteryTemp.0
# .1.3.6.1.4.1.12148.9.3.5.0 0 --> ELTEK-DISTRIBUTED-MIB::batteryBreakerStatus.0

#   .--breaker status------------------------------------------------------.
#   |   _                    _                   _        _                |
#   |  | |__  _ __ ___  __ _| | _____ _ __   ___| |_ __ _| |_ _   _ ___    |
#   |  | '_ \| '__/ _ \/ _` | |/ / _ \ '__| / __| __/ _` | __| | | / __|   |
#   |  | |_) | | |  __/ (_| |   <  __/ |    \__ \ || (_| | |_| |_| \__ \   |
#   |  |_.__/|_|  \___|\__,_|_|\_\___|_|    |___/\__\__,_|\__|\__,_|___/   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                             main check                               |
#   '----------------------------------------------------------------------'


def parse_eltek_battery(string_table):
    if not string_table:
        return None
    voltage, current, temp, breaker_status = string_table[0]
    return {
        "supply": {
            "Supply": {
                "voltage": float(voltage) / 100,
                "current": float(current),
            }
        },
        "temp": float(temp),
        "breaker": breaker_status,
    }


def discover_eltek_battery(parsed):
    if "breaker" in parsed:
        return [(None, None)]
    return []


def check_eltek_battery(_no_item, _no_params, parsed):
    if "breaker" in parsed:
        map_status = {
            "0": (0, "normal"),
            "1": (2, "alarm"),
        }
        state, state_readable = map_status[parsed["breaker"]]
        return state, "Status: %s" % state_readable
    return None


check_info["eltek_battery"] = LegacyCheckDefinition(
    name="eltek_battery",
    detect=DETECT_ELTEK,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12148.9.3",
        oids=["2", "3", "4", "5"],
    ),
    parse_function=parse_eltek_battery,
    service_name="Battery Breaker Status",
    discovery_function=discover_eltek_battery,
    check_function=check_eltek_battery,
)

# .
#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'

# suggested by customer


def discover_eltek_battery_temp(parsed):
    if "temp" in parsed:
        return [("Battery", {})]
    return []


def check_eltek_battery_temp(item, params, parsed):
    # For temp checks we need an item but we have only one
    if "temp" in parsed:
        return check_temperature(parsed["temp"], params, "eltek_battery_temp_Battery")
    return None


check_info["eltek_battery.temp"] = LegacyCheckDefinition(
    name="eltek_battery_temp",
    service_name="Temperature %s",
    sections=["eltek_battery"],
    discovery_function=discover_eltek_battery_temp,
    check_function=check_eltek_battery_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (27.0, 35.0),
    },
)

# .
#   .--phase---------------------------------------------------------------.
#   |                           _                                          |
#   |                     _ __ | |__   __ _ ___  ___                       |
#   |                    | '_ \| '_ \ / _` / __|/ _ \                      |
#   |                    | |_) | | | | (_| \__ \  __/                      |
#   |                    | .__/|_| |_|\__,_|___/\___|                      |
#   |                    |_|                                               |
#   '----------------------------------------------------------------------'


def discover_eltek_battery_supply(section):
    yield from ((item, {}) for item in section["supply"])


def check_eltek_battery_supply(item, params, parsed):
    return check_elphase(item, params, parsed["supply"])


check_info["eltek_battery.supply"] = LegacyCheckDefinition(
    name="eltek_battery_supply",
    service_name="Battery %s",
    sections=["eltek_battery"],
    discovery_function=discover_eltek_battery_supply,
    check_function=check_eltek_battery_supply,
    check_ruleset_name="el_inphase",
    check_default_parameters={
        # suggested by customer
        "voltage": (52, 48),
        "current": (50, 76),
    },
)
