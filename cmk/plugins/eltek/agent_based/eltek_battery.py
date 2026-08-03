#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.eltek.lib import DETECT_ELTEK
from cmk.plugins.lib.elphase import check_elphase, ElPhase
from cmk.plugins.lib.temperature import check_temperature, TempParamType

# .1.3.6.1.4.1.12148.9.3.1.0 --> ELTEK-DISTRIBUTED-MIB::batteryName.0
# .1.3.6.1.4.1.12148.9.3.2.0 5485 --> ELTEK-DISTRIBUTED-MIB::batteryVoltage.0
# .1.3.6.1.4.1.12148.9.3.3.0 0 --> ELTEK-DISTRIBUTED-MIB::batteryCurrent.0
# .1.3.6.1.4.1.12148.9.3.4.0 19 --> ELTEK-DISTRIBUTED-MIB::batteryTemp.0
# .1.3.6.1.4.1.12148.9.3.5.0 0 --> ELTEK-DISTRIBUTED-MIB::batteryBreakerStatus.0


@dataclass(frozen=True)
class Section:
    supply: Mapping[str, ElPhase]
    temp: float
    breaker: str


def parse_eltek_battery(string_table: StringTable) -> Section | None:
    if not string_table:
        return None
    voltage, current, temp, breaker_status = string_table[0]
    return Section(
        supply={
            "Supply": ElPhase.from_dict(
                {
                    "voltage": float(voltage) / 100,
                    "current": float(current),
                }
            )
        },
        temp=float(temp),
        breaker=breaker_status,
    )


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


def discover_eltek_battery(section: Section) -> DiscoveryResult:
    yield Service()


def check_eltek_battery(section: Section) -> CheckResult:
    map_status = {
        "0": (State.OK, "normal"),
        "1": (State.CRIT, "alarm"),
    }
    state, state_readable = map_status[section.breaker]
    yield Result(state=state, summary=f"Status: {state_readable}")


snmp_section_eltek_battery = SimpleSNMPSection(
    name="eltek_battery",
    detect=DETECT_ELTEK,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12148.9.3",
        oids=["2", "3", "4", "5"],
    ),
    parse_function=parse_eltek_battery,
)


check_plugin_eltek_battery = CheckPlugin(
    name="eltek_battery",
    service_name="Battery Breaker Status",
    discovery_function=discover_eltek_battery,
    check_function=check_eltek_battery,
)

#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'

# suggested by customer


def discover_eltek_battery_temp(section: Section) -> DiscoveryResult:
    yield Service(item="Battery")


def check_eltek_battery_temp(item: str, params: TempParamType, section: Section) -> CheckResult:
    # For temp checks we need an item but we have only one
    yield from check_temperature(
        section.temp,
        params,
        unique_name="eltek_battery_temp_Battery",
        value_store=get_value_store(),
    )


check_plugin_eltek_battery_temp = CheckPlugin(
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

#   .--phase---------------------------------------------------------------.
#   |                           _                                          |
#   |                     _ __ | |__   __ _ ___  ___                       |
#   |                    | '_ \| '_ \ / _` / __|/ _ \                      |
#   |                    | |_) | | | | (_| \__ \  __/                      |
#   |                    | .__/|_| |_|\__,_|___/\___|                      |
#   |                    |_|                                               |
#   '----------------------------------------------------------------------'


def discover_eltek_battery_supply(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section.supply)


def check_eltek_battery_supply(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if phase := section.supply.get(item):
        yield from check_elphase(params, phase)


check_plugin_eltek_battery_supply = CheckPlugin(
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
