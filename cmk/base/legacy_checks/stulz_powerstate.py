#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree, StringTable
from cmk.plugins.stulz.lib import DETECT_STULZ

check_info = {}


def discover_stulz_powerstate(info: StringTable) -> list[tuple[str, None]]:
    return [(x[0], None) for x in info]


def check_stulz_powerstate(
    item: str, _no_params: Mapping[str, Any], info: StringTable
) -> tuple[int, str] | tuple[int, str, list[tuple[str, float]]]:
    for line in info:
        if line[0] == item:
            if line[1] != "1":
                message = "Device powered off"
                power_state = 2
            else:
                message = "Device powered on"
                power_state = 6

            return 0, message, [("state", power_state)]
    return 3, "No information found about the device"


def parse_stulz_powerstate(string_table: StringTable) -> StringTable:
    return string_table


check_info["stulz_powerstate"] = LegacyCheckDefinition(
    name="stulz_powerstate",
    parse_function=parse_stulz_powerstate,
    detect=DETECT_STULZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.29462.10.2.1.4.1.1.1.1013",
        oids=[OIDEnd(), "1"],
    ),
    service_name="State %s ",
    discovery_function=discover_stulz_powerstate,
    check_function=check_stulz_powerstate,
)
