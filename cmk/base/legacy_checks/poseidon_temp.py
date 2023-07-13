#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree, startswith


def parse_poseidon_temp(info):
    parsed = {}
    if not info:
        return None
    for name, state, value_string in info:
        try:
            temp = float(value_string.replace("C", ""))
        except ValueError:
            temp = None
        parsed[name] = {"temp": temp, "status": state}
    return parsed


def check_poseidon_temp(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    sensor_states = {
        "0": "invalid",
        "1": "normal",
        "2": "alarmstate",
        "3": "alarm",
    }
    sensor_state_value = data.get("status")
    sensor_state_txt = sensor_states.get(sensor_state_value)
    mk_status = 0
    if sensor_state_value != "1":
        mk_status = 2
    yield mk_status, "Sensor %s, State %s" % (item, sensor_state_txt)

    temp = data.get("temp")
    if temp:
        yield check_temperature(temp, params, "poseidon_temp_%s" % item.replace(" ", "_"))
    else:
        yield 3, "No data for Sensor %s found" % item


def discover_poseidon_temp(section):
    yield from ((item, {}) for item in section)


check_info["poseidon_temp"] = LegacyCheckDefinition(
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.21796.3"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21796.3.3.3.1",
        oids=["2", "4", "5"],
    ),
    parse_function=parse_poseidon_temp,
    service_name="Temperatur: %s",
    discovery_function=discover_poseidon_temp,
    check_function=check_poseidon_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
