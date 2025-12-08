#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

# exemplary output of special agent agent_ucs_bladecenter (<TAB> is tabulator):
#
# <<<ucs_c_rack_server_led:sep(9)>>>
# equipmentIndicatorLed<TAB>dn sys/rack-unit-1/indicator-led-1<TAB>name LED_PSU_STATUS<TAB>color green<TAB>operState on
# equipmentIndicatorLed<TAB>dn sys/rack-unit-1/indicator-led-2<TAB>name LED_TEMP_STATUS<TAB>color green<TAB>operState on
# equipmentIndicatorLed<TAB>dn sys/rack-unit-1/indicator-led-3<TAB>name LED_FAN_STATUS<TAB>color green<TAB>operState on
# equipmentIndicatorLed<TAB>dn sys/rack-unit-1/indicator-led-4<TAB>name LED_HLTH_STATUS<TAB>color green<TAB>operState on
# equipmentIndicatorLed<TAB>dn sys/rack-unit-1/indicator-led-5<TAB>name FP_ID_LED<TAB>color blue<TAB>operState off
# equipmentIndicatorLed<TAB>dn sys/rack-unit-1/indicator-led-0<TAB>name OVERALL_DIMM_STATUS<TAB>color green<TAB>operState on

type Section = Mapping[str, Mapping[str, str]]


def parse_ucs_c_rack_server_led(string_table: StringTable) -> Section:
    """
    >>> parse_ucs_c_rack_server_led([['equipmentIndicatorLed', 'dn sys/rack-unit-1/indicator-led-1', 'name LED_PSU_STATUS', 'color green', 'operState on']])
    {'Rack Unit 1 1': {'Name': 'LED_PSU_STATUS', 'Color': 'green', 'Operational state': 'on'}}
    """
    parsed = dict[str, dict[str, str]]()
    key_translation = {"operState": "Operational state"}

    for led_data in string_table:
        item = led_data[1].split(" ", 1)[1]
        item = (
            item.replace("sys", "")
            .replace("/rack-unit-", "Rack Unit ")
            .replace("/indicator-led-", " ")
        )

        led_dict = {}
        for led_info in led_data[2:]:
            key, value = led_info.split(" ", 1)
            key = key_translation.get(key, key).capitalize()
            led_dict[key] = value

        parsed[item] = led_dict

    return parsed


agent_section_ucs_c_rack_server_led = AgentSection(
    name="ucs_c_rack_server_led",
    parse_function=parse_ucs_c_rack_server_led,
)


def check_ucs_c_rack_server_led(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (led_dict := section.get(item)) is None:
        return
    for k, v in sorted(led_dict.items()):
        if k == "Color":
            state_int = params.get(v, 3)
        else:
            state_int = 0
        state = State(state_int)
        yield Result(state=state, summary=f"{k}: {v}")


def discover_ucs_c_rack_server_led(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


check_plugin_ucs_c_rack_server_led = CheckPlugin(
    name="ucs_c_rack_server_led",
    service_name="LED %s",
    discovery_function=discover_ucs_c_rack_server_led,
    check_function=check_ucs_c_rack_server_led,
    check_ruleset_name="ucs_c_rack_server_led",
    check_default_parameters={
        "amber": 1,
        "blue": 0,
        "green": 0,
        "red": 2,
    },
)
