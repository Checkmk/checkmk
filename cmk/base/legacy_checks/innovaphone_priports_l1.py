#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


import time

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import equals, get_rate, get_value_store, SNMPTree

check_info = {}


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def parse_innovaphone_priports_l1(string_table):
    parsed = {}
    for item, state_s, sigloss_s, slip_s in string_table:
        parsed[item] = {
            "state": saveint(state_s),
            "sigloss": saveint(sigloss_s),
            "slip": saveint(slip_s),
        }
    return parsed


def discover_innovaphone_priports_l1(parsed):
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
    siglos_per_sec = get_rate(
        get_value_store(),
        "innovaphone_priports_l1." + item,
        time.time(),
        l1sigloss,
        raise_overflow=True,
    )
    if siglos_per_sec > 0:
        yield 2, "Signal loss is %.2f/sec" % siglos_per_sec

    l1slip = data["slip"]
    if l1slip > params.get("err_slip_count", 0):
        yield 2, "Slip error count at %d" % l1slip


check_info["innovaphone_priports_l1"] = LegacyCheckDefinition(
    name="innovaphone_priports_l1",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.6666"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6666.1.2.1",
        oids=["1", "2", "5", "9"],
    ),
    parse_function=parse_innovaphone_priports_l1,
    service_name="Port L1 %s",
    discovery_function=discover_innovaphone_priports_l1,
    check_function=check_innovaphone_priports_l1,
    check_default_parameters={},
)
