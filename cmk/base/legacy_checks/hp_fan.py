#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator, Mapping

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, any_of, contains, OIDEnd, SNMPTree, StringTable

check_info = {}


def parse_hp_fan(string_table: StringTable) -> Mapping[str, str]:
    return {
        f"{tray_index}/{fan_index}": fan_state for fan_index, tray_index, fan_state in string_table
    }


def discover_hp_fan(parsed: Mapping[str, str]) -> Iterator[tuple[str, None]]:
    for fan in parsed:
        yield fan, None


def check_hp_fan(item: str, _no_params: object, parsed: Mapping[str, str]) -> tuple[int, str]:
    statemap = {
        "0": (3, "unknown"),
        "1": (2, "removed"),
        "2": (2, "off"),
        "3": (1, "underspeed"),
        "4": (1, "overspeed"),
        "5": (0, "ok"),
        "6": (3, "maxstate"),
    }
    return statemap[parsed[item]]


check_info["hp_fan"] = LegacyCheckDefinition(
    name="hp_fan",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "hp"),
        any_of(
            contains(".1.3.6.1.2.1.1.1.0", "5406rzl2"), contains(".1.3.6.1.2.1.1.1.0", "5412rzl2")
        ),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11.2.14.11.5.1.54.2.1.1",
        oids=[OIDEnd(), "2", "4"],
    ),
    parse_function=parse_hp_fan,
    service_name="Fan %s",
    discovery_function=discover_hp_fan,
    check_function=check_hp_fan,
)
