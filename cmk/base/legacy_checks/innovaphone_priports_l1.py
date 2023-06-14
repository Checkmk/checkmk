#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

from cmk.base.check_api import get_rate, LegacyCheckDefinition, saveint
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import equals, SNMPTree


def parse_innovaphone_priports_l1(info):
    parsed = {}
    for item, state_s, sigloss_s, slip_s in info:
        parsed[item] = {
            "state": saveint(state_s),
            "sigloss": saveint(sigloss_s),
            "slip": saveint(slip_s),
        }
    return parsed


def inventory_innovaphone_priports_l1(parsed):
    return [
        (item, {"err_slip_count": data["slip"]})
        for item, data in parsed.items()
        if data["state"] != 1
    ]


def check_innovaphone_priports_l1(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    states = {
        1: "Down",
        2: "UP",
    }

    l1state = data["state"]
    yield 0 if l1state == 2 else 2, "Current state is %s" % states[l1state]

    l1sigloss = data["sigloss"]
    siglos_per_sec = get_rate("innovaphone_priports_l1." + item, time.time(), l1sigloss)
    if siglos_per_sec > 0:
        yield 2, "Signal loss is %.2f/sec" % siglos_per_sec

    l1slip = data["slip"]
    if l1slip > params.get("err_slip_count", 0):
        yield 2, "Slip error count at %d" % l1slip


check_info["innovaphone_priports_l1"] = LegacyCheckDefinition(
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.6666"),
    parse_function=parse_innovaphone_priports_l1,
    discovery_function=inventory_innovaphone_priports_l1,
    check_function=check_innovaphone_priports_l1,
    service_name="Port L1 %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6666.1.2.1",
        oids=["1", "2", "5", "9"],
    ),
)
