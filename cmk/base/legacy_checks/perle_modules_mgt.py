#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Generator, Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition, LegacyResult
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.perle.lib import DETECT_PERLE

check_info = {}

# .1.3.6.1.4.1.1966.21.1.1.1.1.4.5.1.1.2.1.1 1 --> PERLE-MCR-MGT-MIB::mcrMgtSlotIndex.1.1
# .1.3.6.1.4.1.1966.21.1.1.1.1.4.5.1.1.3.1.1 MCR-MGT --> PERLE-MCR-MGT-MIB::mcrMgtModelName.1.1
# .1.3.6.1.4.1.1966.21.1.1.1.1.4.5.3.1.4.1.1 0 --> PERLE-MCR-MGT-MIB::mcrMgtLedALM.1.1


def discover_perle_modules_mgt(info: StringTable) -> list[tuple[str, None]]:
    return [(index, None) for index, _name, _descr, _alarm_led, _status in info]


def check_perle_modules_mgt(
    item: str, _no_params: Mapping[str, Any], info: StringTable
) -> Generator[LegacyResult]:
    mappings = {
        "alarm_led": {
            "0": (0, "no alarms"),
            "1": (2, "alarms present"),
        },
        "power_led": {
            "0": (2, "off"),
            "1": (0, "on"),
        },
    }

    for index, _name, _descr, power_led, alarm_led in info:
        if item == index:
            for title, value, key in [
                ("Alarm LED", alarm_led, "alarm_led"),
                ("Power LED", power_led, "power_led"),
            ]:
                state, state_readable = mappings[key][value]
                yield state, f"{title}: {state_readable}"


def parse_perle_modules_mgt(string_table: StringTable) -> StringTable:
    return string_table


check_info["perle_modules_mgt"] = LegacyCheckDefinition(
    name="perle_modules_mgt",
    parse_function=parse_perle_modules_mgt,
    detect=DETECT_PERLE,
    # If you change snmp info please adapt the related inventory plugin,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1966.21.1.1.1.1.4.5",
        oids=["1.1.2", "1.1.3", "1.1.4", "3.1.3", "3.1.4"],
    ),
    service_name="Chassis slot %s MGT",
    discovery_function=discover_perle_modules_mgt,
    check_function=check_perle_modules_mgt,
)
