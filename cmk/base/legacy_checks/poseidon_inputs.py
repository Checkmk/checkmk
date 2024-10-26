#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith

check_info = {}


def parse_poseidon_inputs(string_table):
    parsed = {}
    if string_table:
        for line_number, line in enumerate(string_table, 1):
            input_value, input_name, input_alarm_setup, input_alarm_state = line
            if input_name == "":
                input_name = "Eingang %d" % line_number
            try:
                input_value = int(input_value)
            except ValueError:
                input_value = 3
            try:
                input_alarm_setup = int(input_alarm_setup)
            except ValueError:
                input_alarm_setup = 3
            try:
                input_alarm_state = int(input_alarm_state)
            except ValueError:
                input_alarm_state = 3
            parsed[input_name] = {
                "input_value": input_value,
                "input_alarm_setup": input_alarm_setup,
                "input_alarm_state": input_alarm_state,
            }
        return parsed
    return None


def check_poseidon_inputs(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    alarm_setup = {0: "inactive", 1: "activeOff", 2: "activeOn", 3: "unkown"}
    input_values = {0: "off", 1: "on", 3: "unkown"}
    alarm_states = {0: "normal", 1: "alarm", 3: "unkown"}
    txt = "{}: AlarmSetup: {}".format(item, alarm_setup[data.get("input_alarm_setup", 3)])
    yield 0, txt

    state = data.get("input_alarm_state", 3)
    txt = "Alarm State: %s" % alarm_states[state]
    if state == 1:
        state = 2
    yield state, txt

    yield 0, "Values %s" % input_values.get(data.get("input_value", 3), "unknown")


def discover_poseidon_inputs(section):
    yield from ((item, {}) for item in section)


check_info["poseidon_inputs"] = LegacyCheckDefinition(
    name="poseidon_inputs",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.21796.3"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21796.3.3.1.1",
        oids=["2", "3", "4", "5"],
    ),
    parse_function=parse_poseidon_inputs,
    service_name="%s",
    discovery_function=discover_poseidon_inputs,
    check_function=check_poseidon_inputs,
)
