#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)

Section = Mapping[str, Mapping[str, int]]


def parse_poseidon_inputs(string_table: StringTable) -> Section | None:
    parsed: dict[str, dict[str, int]] = {}
    if string_table:
        for line_number, line in enumerate(string_table, 1):
            input_value_str, input_name, input_alarm_setup_str, input_alarm_state_str = line
            if input_name == "":
                input_name = f"Eingang {line_number}"
            try:
                input_value = int(input_value_str)
            except ValueError:
                input_value = 3
            try:
                input_alarm_setup = int(input_alarm_setup_str)
            except ValueError:
                input_alarm_setup = 3
            try:
                input_alarm_state = int(input_alarm_state_str)
            except ValueError:
                input_alarm_state = 3
            parsed[input_name] = {
                "input_value": input_value,
                "input_alarm_setup": input_alarm_setup,
                "input_alarm_state": input_alarm_state,
            }
        return parsed
    return None


def check_poseidon_inputs(item: str, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    alarm_setup = {0: "inactive", 1: "activeOff", 2: "activeOn", 3: "unkown"}
    input_values = {0: "off", 1: "on", 3: "unkown"}
    alarm_states = {0: "normal", 1: "alarm", 3: "unkown"}
    alarm_setup_value = data.get("input_alarm_setup", 3)
    txt = f"{item}: AlarmSetup: {alarm_setup[alarm_setup_value]}"
    yield Result(state=State.OK, summary=txt)

    state_value = data.get("input_alarm_state", 3)
    txt = f"Alarm State: {alarm_states[state_value]}"
    state = State.CRIT if state_value == 1 else State.OK
    yield Result(state=state, summary=txt)

    input_val = data.get("input_value", 3)
    yield Result(
        state=State.OK,
        summary=f"Values {input_values.get(input_val, 'unknown')}",
    )


def discover_poseidon_inputs(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


snmp_section_poseidon_inputs = SimpleSNMPSection(
    name="poseidon_inputs",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.21796.3"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21796.3.3.1.1",
        oids=["2", "3", "4", "5"],
    ),
    parse_function=parse_poseidon_inputs,
)


check_plugin_poseidon_inputs = CheckPlugin(
    name="poseidon_inputs",
    service_name="%s",
    discovery_function=discover_poseidon_inputs,
    check_function=check_poseidon_inputs,
)
