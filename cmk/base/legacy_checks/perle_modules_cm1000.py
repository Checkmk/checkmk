#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from collections.abc import Mapping

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.perle.lib import DETECT_PERLE

check_info = {}


def parse_perle_modules(string_table: StringTable) -> StringTable:
    return string_table


def discover_perle_cm_modules(info):
    yield from ((index, {}) for _name, _led, index, *_rest in info)


MAP_SPEED: Mapping[str, str] = {
    "0": "10 Mbs",
    "1": "100 Mbps",
    "2": "1000 Mbps",
}

MAP_POWER_LED: Mapping[str, tuple[int, str]] = {
    "0": (2, "no power"),
    "1": (0, "power to the module"),
    "2": (0, "loopback enabled"),
}

MAP_FIBER_LPRF: Mapping[str, tuple[int, str]] = {
    "0": (0, "ok"),
    "1": (2, "offline"),
    "2": (2, "link fault"),
    "3": (2, "auto neg error"),
    # available for cm1110 modules
    "99": (2, "not applicable"),
}
MAP_FIBER_LINK: Mapping[str, tuple[int, str]] = {
    "0": (1, "down"),
    "1": (0, "up"),
}

MAP_FIBER_CONNECTOR: Mapping[str, str] = {
    "0": "sc",
    "1": "lc",
    "2": "st",
    "3": "sfp",
    "5": "fc",
    "6": "mtrj",
}
MAP_COPPER_LPRF: Mapping[str, tuple[int, str]] = {
    "0": (0, "ok"),
    "1": (2, "remote fault"),
}

MAP_COPPER_LINK: Mapping[str, tuple[int, str]] = {
    "0": (1, "down"),
    "1": (0, "ok"),
}

MAP_COPPER_CONNECTOR: Mapping[str, str] = {
    "0": "rj45",
}


def check_perle_cm_modules(item, _no_params, info):
    for (
        _name,
        power_led,
        index,
        fiber_lprf,
        fiber_link,
        fiber_connector,
        fiber_speed,
        cooper_lprf,
        copper_link,
        copper_connector,
        copper_speed,
    ) in info:
        if item != index:
            continue

        state, state_readable = MAP_POWER_LED[power_led]
        yield state, "Power status: %s" % state_readable

        yield 0, f"Fiber speed: {MAP_SPEED[fiber_speed]}"
        state, state_readable = MAP_FIBER_LPRF[fiber_lprf]
        yield state, f"LPRF: {state_readable}"
        state, state_readable = MAP_FIBER_LINK[fiber_link]
        yield state, f"Link: {state_readable}"
        yield 0, f"Connector: {MAP_FIBER_CONNECTOR[fiber_connector]}"

        yield 0, f"Copper speed: {MAP_SPEED[copper_speed]}"
        state, state_readable = MAP_COPPER_LPRF[cooper_lprf]
        yield state, f"LPRF: {state_readable}"
        state, state_readable = MAP_COPPER_LINK[copper_link]
        yield state, f"Link: {state_readable}"
        yield 0, f"Connector: {MAP_COPPER_CONNECTOR[copper_connector]}"


check_info["perle_modules_cm1110"] = LegacyCheckDefinition(
    name="perle_modules_cm1110",
    parse_function=parse_perle_modules,
    detect=DETECT_PERLE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1966.21.1.1.1.1.4.3",
        oids=[
            "1.1.3",
            "3.1.3",
            "1.1.2",
            "1.1.21",
            "1.1.15",
            "1.1.16",
            "1.1.18",
            "1.1.32",
            "1.1.25",
            "1.1.26",
            "1.1.28",
        ],
    ),
    service_name="Chassis slot %s CM1110",
    discovery_function=discover_perle_cm_modules,
    check_function=check_perle_cm_modules,
)


check_info["perle_modules_cm1000"] = LegacyCheckDefinition(
    name="perle_modules_cm1000",
    parse_function=parse_perle_modules,
    detect=DETECT_PERLE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1966.21.1.1.1.1.4.1",
        oids=[
            "1.1.3",
            "3.1.3",
            "1.1.2",
            "1.1.18",
            "1.1.12",
            "1.1.13",
            "1.1.15",
            "1.1.28",
            "1.1.21",
            "1.1.22",
            "1.1.24",
        ],
    ),
    service_name="Chassis slot %s CM1000",
    discovery_function=discover_perle_cm_modules,
    check_function=check_perle_cm_modules,
)
