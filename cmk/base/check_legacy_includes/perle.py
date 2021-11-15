#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file


def perle_scan_function(oid):
    return oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.1966.20")


def perle_check_alarms(alarms_str):
    state = 0
    alarminfo = ""
    if int(alarms_str) > 0:
        state = 2
        alarminfo += " (User intervention is needed to resolve the outstanding alarms)"

    return state, "Alarms: %s%s" % (alarms_str, alarminfo)


#   .--modules-------------------------------------------------------------.
#   |                                   _       _                          |
#   |               _ __ ___   ___   __| |_   _| | ___  ___                |
#   |              | '_ ` _ \ / _ \ / _` | | | | |/ _ \/ __|               |
#   |              | | | | | | (_) | (_| | |_| | |  __/\__ \               |
#   |              |_| |_| |_|\___/ \__,_|\__,_|_|\___||___/               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


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
            state, state_readable = mappings["power_led"][power_led]
            yield state, "Power status: %s" % state_readable

            for what, lprf, link, speed, connector in [
                ("Fiber", fiber_lprf, fiber_link, fiber_speed, fiber_connector),
                ("Copper", cooper_lprf, copper_link, copper_speed, copper_connector),
            ]:

                yield 0, "%s Speed: %s" % (what, mappings["speed"][speed])

                for what_state, what_key in [(lprf, "LPRF"), (link, "Link")]:
                    state, state_readable = mappings["%s_%s" % (what.lower(), what_key.lower())][
                        what_state
                    ]
                    yield state, "%s: %s" % (what_key, state_readable)

                yield 0, "Connector: %s" % mappings["%s_connector" % what.lower()][connector]
