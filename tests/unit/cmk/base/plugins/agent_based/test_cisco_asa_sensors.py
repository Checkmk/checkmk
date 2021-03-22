#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based.cisco_asa_sensors import (
    CiscoAsaPowerSensor,
    CiscoAsaTempSensor,
    CiscoAsaFanSensor,
    CiscoAsaSensors,
    get_status_readable,
    get_sensor_state,
    parse_cisco_asa_sensors,
)

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    State,
)


@pytest.mark.parametrize("string_table,expected_parsed_data", [
    (
            [[
                ['Chassis', '', '', '', ''],
                ['Processor 0/0', '', '', '', ''],
                ['Processor 0/1', '', '', '', ''],
                ['Processor 0/2', '', '', '', ''],
                ['ASA5515 Slot for Removable Drive 0', '', '', '', ''],
                ['Micron_M550_MTFDDAK128MAY Removable Drive in Slot 0', '', '', '', ''],
                ['Chassis Cooling Fan 1', '', '', '', ''],
                ['Chassis Fan Sensor 1', '10', '7680', '1', 'rpm'],
                ['Chassis Cooling Fan 2', '', '', '', ''],
                ['Chassis Fan Sensor 2', '10', '7936', '1', 'rpm'],
                ['Chassis Cooling Fan 3', '', '', '', ''],
                ['Chassis Fan Sensor 3', '10', '7680', '1', 'rpm'],
                ['CPU Temperature Sensor 0/0', '8', '34', '1', 'celsius'],
                ['Chassis Ambient Temperature Sensor 1', '8', '32', '1', 'celsius'],
                ['Chassis Ambient Temperature Sensor 2', '8', '30', '1', 'celsius'],
                ['Chassis Ambient Temperature Sensor 3', '8', '33', '1', 'celsius'],
                ['Power supply 1', '12', '', '3', ''],
                ['Power supply 2', '12', '', '1', ''],
                ['Gi0/0', '', '', '', ''],
                ['Gi0/1', '', '', '', ''],
                ['Gi0/2', '', '', '', ''],
                ['Gi0/3', '', '', '', ''],
                ['Gi0/4', '', '', '', ''],
                ['Gi0/5', '', '', '', ''],
                ['In0/0', '', '', '', ''],
                ['In0/1', '', '', '', ''],
                ['Ma0/0', '', '', '', ''],
                ['Po1', '', '', '', '']
            ]],
            CiscoAsaSensors(
                temp={
                    'CPU Sensor 0/0': CiscoAsaTempSensor(value=34.0, state=State.OK, status=0, status_readable='Ok',
                                                         unit='celsius'),
                    'Chassis Ambient Sensor 1': CiscoAsaTempSensor(value=32.0, state=State.OK, status=0,
                                                                   status_readable='Ok', unit='celsius'),
                    'Chassis Ambient Sensor 2': CiscoAsaTempSensor(value=30.0, state=State.OK, status=0,
                                                                   status_readable='Ok', unit='celsius'),
                    'Chassis Ambient Sensor 3': CiscoAsaTempSensor(value=33.0, state=State.OK, status=0,
                                                                   status_readable='Ok', unit='celsius')},
                fan={
                    'Chassis Sensor 1': CiscoAsaFanSensor(value=7680, state=State.OK, status_readable='Ok', unit='rpm'),
                    'Chassis Sensor 2': CiscoAsaFanSensor(value=7936, state=State.OK, status_readable='Ok', unit='rpm'),
                    'Chassis Sensor 3': CiscoAsaFanSensor(value=7680, state=State.OK, status_readable='Ok',
                                                          unit='rpm')},
                power={'supply 1': CiscoAsaPowerSensor(state=State.CRIT, status_readable='nonoperational'),
                       'supply 2': CiscoAsaPowerSensor(state=State.OK, status_readable='Ok')
                       })
            ,
    ),
])
def test_parse_cisco_asa_sensors(string_table, expected_parsed_data):
    assert parse_cisco_asa_sensors(string_table) == expected_parsed_data


if __name__ == "__main__":
    pytest.main(["-vvsx", "-T", "unit", __file__])
