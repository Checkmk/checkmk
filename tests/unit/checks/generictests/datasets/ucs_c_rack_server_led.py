#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based.ucs_c_rack_server_led import parse_ucs_c_rack_server_led

checkname = 'ucs_c_rack_server_led'

parsed = parse_ucs_c_rack_server_led([
    ['equipmentIndicatorLed', 'dn sys/rack-unit-1/indicator-led-1', 'name LED_PSU_STATUS',
     'color green', 'operState on'],
    ['equipmentIndicatorLed', 'dn sys/rack-unit-1/indicator-led-2', 'name LED_PSU_STATUS',
     'color blue', 'operState on'],
    ['equipmentIndicatorLed', 'dn sys/rack-unit-1/indicator-led-3', 'name LED_PSU_STATUS',
     'color amber', 'operState on'],
    ['equipmentIndicatorLed', 'dn sys/rack-unit-1/indicator-led-4', 'name LED_PSU_STATUS',
     'color red', 'operState on'],
    ['equipmentIndicatorLed', 'dn sys/rack-unit-1/indicator-led-5', 'name LED_PSU_STATUS',
     'color orange', 'operState on'],
])

discovery = {'': [('Rack Unit 1 1', {}),
                  ('Rack Unit 1 2', {}),
                  ('Rack Unit 1 3', {}),
                  ('Rack Unit 1 4', {}),
                  ('Rack Unit 1 5', {})]}

_factory_settings = {
    "amber": 1,
    "blue": 0,
    "green": 0,
    "red": 2,
}

checks = {'': [('Rack Unit 1 1',
                _factory_settings,
                [(0, 'Color: green'), (0, 'Name: LED_PSU_STATUS'), (0, 'Operational state: on')]),
               ('Rack Unit 1 2',
                _factory_settings,
                [(0, 'Color: blue'), (0, 'Name: LED_PSU_STATUS'), (0, 'Operational state: on')]),
               ('Rack Unit 1 3',
                _factory_settings,
                [(1, 'Color: amber'), (0, 'Name: LED_PSU_STATUS'), (0, 'Operational state: on')]),
               ('Rack Unit 1 4',
                _factory_settings,
                [(2, 'Color: red'), (0, 'Name: LED_PSU_STATUS'), (0, 'Operational state: on')]),
               ('Rack Unit 1 5',
                _factory_settings,
                [(3, 'Color: orange'), (0, 'Name: LED_PSU_STATUS'), (0, 'Operational state: on')]),
               ]}
