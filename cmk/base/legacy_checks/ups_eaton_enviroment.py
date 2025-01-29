#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import any_of, equals, SNMPTree, StringTable

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


def inventory_ups_eaton_enviroment(info):
    if len(info) > 0:
        return [(None, {})]
    return []


def check_ups_eaton_enviroment(item, params, info):
    wert = list(map(saveint, info[0]))
    i = 0
    state = 0
    messages = []
    perfdata = []
    for sensor, sensor_name, unit_symbol in [
        ("temp", "Temperature", " °C"),
        ("remote_temp", "Remote-Temperature", " °C"),
        ("humidity", "Humidity", "%"),
    ]:
        warn, crit = params.get(sensor)
        perfdata.append((sensor, wert[i], warn, crit))
        text = "%s: %d%s (warn/crit at %d%s/%d%s)" % (
            sensor_name,
            wert[i],
            unit_symbol,
            warn,
            unit_symbol,
            crit,
            unit_symbol,
        )

        if wert[i] >= crit:
            state = 2
            text += "(!!)"
        elif wert[i] >= warn:
            state = max(state, 1)
            text += "(!)"

        i += 1
        messages.append(text)

    return (state, ", ".join(messages), perfdata)


def parse_ups_eaton_enviroment(string_table: StringTable) -> StringTable:
    return string_table


check_info["ups_eaton_enviroment"] = LegacyCheckDefinition(
    name="ups_eaton_enviroment",
    parse_function=parse_ups_eaton_enviroment,
    detect=any_of(
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.705.1.2"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.534.1"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.705.1"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.534.1.6",
        oids=["1", "5", "6"],
    ),
    service_name="Enviroment",
    discovery_function=inventory_ups_eaton_enviroment,
    check_function=check_ups_eaton_enviroment,
    check_ruleset_name="eaton_enviroment",
    check_default_parameters={
        "temp": (40, 50),
        "remote_temp": (40, 50),
        "humidity": (65, 80),
    },
)
