#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# exemplary output of special agent agent_ucs_bladecenter (<TAB> is tabulator):
#
# <<<ucs_c_rack_server_led:sep(9)>>>
# equipmentIndicatorLed<TAB>dn sys/rack-unit-1/indicator-led-1<TAB>name LED_PSU_STATUS<TAB>color green<TAB>operState on
# equipmentIndicatorLed<TAB>dn sys/rack-unit-1/indicator-led-2<TAB>name LED_TEMP_STATUS<TAB>color green<TAB>operState on
# equipmentIndicatorLed<TAB>dn sys/rack-unit-1/indicator-led-3<TAB>name LED_FAN_STATUS<TAB>color green<TAB>operState on
# equipmentIndicatorLed<TAB>dn sys/rack-unit-1/indicator-led-4<TAB>name LED_HLTH_STATUS<TAB>color green<TAB>operState on
# equipmentIndicatorLed<TAB>dn sys/rack-unit-1/indicator-led-5<TAB>name FP_ID_LED<TAB>color blue<TAB>operState off
# equipmentIndicatorLed<TAB>dn sys/rack-unit-1/indicator-led-0<TAB>name OVERALL_DIMM_STATUS<TAB>color green<TAB>operState on

from typing import Dict

from .agent_based_api.v1 import register, type_defs


def parse_ucs_c_rack_server_led(string_table: type_defs.StringTable) -> Dict[str, Dict]:
    """
    >>> parse_ucs_c_rack_server_led([['equipmentIndicatorLed', 'dn sys/rack-unit-1/indicator-led-1', 'name LED_PSU_STATUS', 'color green', 'operState on']])
    {'Rack Unit 1 1': {'Name': 'LED_PSU_STATUS', 'Color': 'green', 'Operational state': 'on'}}
    """
    parsed = {}
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


register.agent_section(
    name="ucs_c_rack_server_led",
    parse_function=parse_ucs_c_rack_server_led,
)
