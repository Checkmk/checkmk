#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.fan import check_fan
from cmk.plugins.lib.primekey import DETECT_PRIMEKEY


@dataclass(frozen=True)
class Fan:
    speed: float
    state_fail: bool


_Section = Mapping[str, Fan]


def parse(string_table: StringTable) -> _Section | None:
    if not string_table:
        return None

    fan_data = string_table[0]

    system_fans_failed = bool(int(fan_data[5]))
    cpu_fan_failed = bool(int(fan_data[4]))

    parsed = {
        "1": Fan(speed=float(fan_data[1]), state_fail=system_fans_failed),
        "2": Fan(speed=float(fan_data[2]), state_fail=system_fans_failed),
        "3": Fan(speed=float(fan_data[3]), state_fail=system_fans_failed),
        "CPU": Fan(speed=float(fan_data[0]), state_fail=cpu_fan_failed),
    }

    return parsed


snmp_section_primekey_fan = SimpleSNMPSection(
    name="primekey_fan",
    parse_function=parse,
    detect=DETECT_PRIMEKEY,
    fetch=SNMPTree(
        ".1.3.6.1.4.1.22408.1.1.2.1.4.102.97.110",
        [
            "49.1",  # rpm cpu fan
            "50.1",  # rpm system fan 1
            "51.1",  # rpm system fan 2
            "52.1",  # rpm system fan 3
            "53.1",  # status cpu fan
            "54.1",  # status system fans
        ],
    ),
)


def discover(section: _Section) -> DiscoveryResult:
    for item in section.keys():
        yield Service(item=item)


def check(
    item: str,
    params: Mapping[str, Any],
    section: _Section,
) -> CheckResult:
    if not (fan := section.get(item)):
        return

    if fan.state_fail:
        yield Result(state=State.CRIT, notice=f"Status {item} fan not OK")

    yield from check_fan(fan.speed, params)


check_plugin_primekey_fan = CheckPlugin(
    name="primekey_fan",
    service_name="PrimeKey Fan %s",
    discovery_function=discover,
    check_function=check,
    check_default_parameters={"lower": (1000, 0), "output_metrics": True},
    check_ruleset_name="hw_fans",
)
