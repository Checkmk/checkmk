#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.temperature import check_temperature

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith

check_info = {}

# Example:
# .1.3.6.1.4.1.89.53.15.1.9.1 = INTEGER: 42
# .1.3.6.1.4.1.89.53.15.1.10.1 = INTEGER: ok(1)

# Temperature is in Celcius by default.
# Tested with Dell PowerConnect 5448 and 5424 models.


def parse_dell_powerconnect_temp(string_table):
    try:
        temp_str, dev_status = string_table[0]
    except (IndexError, ValueError):
        return None
    try:
        temp = float(temp_str)
    except ValueError:
        temp = None
    return (
        temp,
        {
            "1": "OK",
            "2": "unavailable",
            "3": "non operational",
        }.get(dev_status, "unknown[%s]" % dev_status),
    )


def inventory_dell_powerconnect_temp(parsed):
    if parsed:
        return [("Ambient", {})]
    return []


def check_dell_powerconnect_temp(_no_item, params, parsed):
    if parsed is None:
        return None

    temp, dev_state_readable = parsed
    if dev_state_readable == "OK":
        state = 0
    elif dev_state_readable == "unavailable":
        state = 1
    elif dev_state_readable == "non operational":
        state = 2
    else:
        state = 3

    if temp is None:
        return state, "Status: %s" % dev_state_readable
    return check_temperature(
        temp, params, "dell_powerconnect", dev_status=state, dev_status_name=dev_state_readable
    )


check_info["dell_powerconnect_temp"] = LegacyCheckDefinition(
    name="dell_powerconnect_temp",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.674.10895"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.89.53.15.1",
        oids=["9", "10"],
    ),
    parse_function=parse_dell_powerconnect_temp,
    service_name="Temperature %s",
    discovery_function=inventory_dell_powerconnect_temp,
    check_function=check_dell_powerconnect_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (35.0, 40.0),
    },
)
