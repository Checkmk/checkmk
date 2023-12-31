#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree
from cmk.agent_based.v2.type_defs import StringTable
from cmk.plugins.lib.perle import DETECT_PERLE


def parse_perle_modules(string_table: StringTable) -> StringTable:
    return string_table


def inventory_perle_cm_modules(info):
    inventory = []
    for (
        _name,
        _led,
        index,
        _fiber_lprf,
        _fiber_link,
        _fiber_conn,
        _fiber_speed,
        _cooper_lprf,
        _copper_link,
        _copper_conn,
        _copper_speed,
    ) in info:
        inventory.append((index, None))
    return inventory


def check_perle_cm_modules(item, _no_params, info):
    mappings = {
        "speed": {
            "0": "10 Mbs",
            "1": "100 Mbps",
            "2": "1000 Mbps",
        },
        "power_led": {
            "0": (2, "no power"),
            "1": (0, "power to the module"),
            "2": (0, "loopback enabled"),
        },
        "fiber_lprf": {
            "0": (0, "ok"),
            "1": (2, "offline"),
            "2": (2, "link fault"),
            "3": (2, "auto neg error"),
            # available for cm1110 modules
            "99": (2, "not applicable"),
        },
        "fiber_link": {
            "0": (1, "down"),
            "1": (0, "up"),
        },
        "fiber_connector": {
            "0": "sc",
            "1": "lc",
            "2": "st",
            "3": "sfp",
            "5": "fc",
            "6": "mtrj",
        },
        "copper_lprf": {
            "0": (0, "ok"),
            "1": (2, "remote fault"),
        },
        "copper_link": {
            "0": (1, "down"),
            "1": (0, "ok"),
        },
        "copper_connector": {
            "0": "rj45",
        },
    }

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
        if item == index:
            state, state_readable = mappings["power_led"][power_led]  # type: ignore[index]
            yield state, "Power status: %s" % state_readable

            for what, lprf, link, speed, connector in [
                ("Fiber", fiber_lprf, fiber_link, fiber_speed, fiber_connector),
                ("Copper", cooper_lprf, copper_link, copper_speed, copper_connector),
            ]:
                yield 0, "{} Speed: {}".format(what, mappings["speed"][speed])  # type: ignore[index]

                for what_state, what_key in [(lprf, "LPRF"), (link, "Link")]:
                    state, state_readable = mappings[f"{what.lower()}_{what_key.lower()}"][  # type: ignore[index]
                        what_state
                    ]
                    yield state, f"{what_key}: {state_readable}"

                yield 0, "Connector: %s" % mappings["%s_connector" % what.lower()][connector]  # type: ignore[index]


check_info["perle_modules_cm1110"] = LegacyCheckDefinition(
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
    discovery_function=inventory_perle_cm_modules,
    check_function=check_perle_cm_modules,
)


check_info["perle_modules_cm1000"] = LegacyCheckDefinition(
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
    discovery_function=inventory_perle_cm_modules,
    check_function=check_perle_cm_modules,
)
