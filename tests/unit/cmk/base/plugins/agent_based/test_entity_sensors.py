#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from cmk.base.plugins.agent_based.entity_sensors import (
    check_entity_sensors_fan,
    check_entity_sensors_power_presence,
    check_entity_sensors_temp,
    discover_entity_sensors_fan,
    discover_entity_sensors_power_presence,
    discover_entity_sensors_temp,
    EntitySensor,
    parse_entity_sensors,
)
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Metric,
    Result,
    Service,
    State,
)


@pytest.mark.parametrize("string_table, expected_section", [
    (
        [
            [
                ['1', 'PA-500'],
                ['2', 'Fan #1 Operational'],
                ['3', 'Fan #2 Operational'],
                ['4', 'Temperature at MP [U6]'],
                ['5', 'Temperature at DP [U7]'],
            ],
            [
                ['2', '10', '9', '1', '1', 'rpm'],
                ['3', '10', '9', '1', '1', 'rpm'],
                ['4', '8', '9', '37', '1', 'celsius'],
                ['5', '8', '9', '40', '1', 'fahrenheit'],
            ],
        ],
        {
            'fan': {
                'Sensor 1 Operational': EntitySensor(
                    name='Sensor 1 Operational',
                    unit='RPM',
                    reading=1.0,
                    status_descr='OK',
                    state=State.OK,
                ),
                'Sensor 2 Operational': EntitySensor(
                    name='Sensor 2 Operational',
                    unit='RPM',
                    reading=1.0,
                    status_descr='OK',
                    state=State.OK,
                ),
            },
            'temp': {
                'Sensor at MP [U6]': EntitySensor(
                    name='Sensor at MP [U6]',
                    unit='c',
                    reading=37.0,
                    status_descr='OK',
                    state=State.OK,
                ),
                'Sensor at DP [U7]': EntitySensor(
                    name='Sensor at DP [U7]',
                    unit='f',
                    reading=40.0,
                    status_descr='OK',
                    state=State.OK,
                ),
            },
        },
    ),
    (
        [
            [
                ['1', 'Chassis'],
                ['2', 'Processor 0/0'],
                ['3', 'Processor 0/1'],
                ['4', 'Processor 0/2'],
                ['5', 'Processor 0/3'],
                ['6', 'Processor 0/4'],
                ['7', 'Processor 0/5'],
                ['8', 'Processor 0/6'],
                ['9', 'Processor 0/7'],
                ['10', 'AS Slot for Removable Drive 0'],
                ['11', 'AS5 Slot for Removable Drive 1'],
                ['12', 'Mi_M6 Removable Drive in Slot 0'],
                ['13', 'Mi_M6_M Removable Drive in Slot 1'],
                ['14', 'Chassis Cooling Fan 1'],
                ['15', 'Chassis Fan Sensor 1'],
                ['16', 'Chassis Cooling Fan 2'],
                ['17', 'Chassis Fan Sensor 2'],
                ['18', 'Chassis Cooling Fan 3'],
                ['19', 'Chassis Fan Sensor 3'],
                ['20', 'Power Supply 0'],
                ['21', 'Power Supply 0 Presence Sensor'],
                ['22', 'Power Supply 0 Input Sensor'],
                ['23', 'Power Supply 0 Fan'],
                ['24', 'Power Supply 0 Fan Sensor'],
                ['25', 'Power Supply 0 Temperature Sensor'],
                ['26', 'Power Supply 1'],
                ['27', 'Power Supply 1 Presence Sensor'],
                ['28', 'Power Supply 1 Input Sensor'],
                ['29', 'Power Supply 1 Fan'],
                ['30', 'Power Supply 1 Fan Sensor'],
                ['31', 'Power Supply 1 Temperature Sensor'],
                ['32', 'CPU Temperature Sensor 0/0'],
                ['33', 'Chassis Ambient Temperature Sensor 1'],
                ['34', 'Chassis Ambient Temperature Sensor 2'],
                ['35', 'Chassis Ambient Temperature Sensor 3'],
                ['36', 'G0'],
                ['37', 'G1'],
                ['38', 'G2'],
                ['39', 'G3'],
                ['40', 'G4'],
                ['41', 'G5'],
                ['42', 'G6'],
                ['43', 'G7'],
                ['44', 'I0'],
                ['45', 'I1'],
                ['46', 'M0'],
            ],
            [
                ['15', '10', '9', '4864', '1', 'rpm'],
                ['17', '10', '9', '4864', '1', 'rpm'],
                ['19', '10', '9', '4864', '1', 'rpm'],
                ['21', '12', '9', '1', '1', 'truthvalue'],
                ['22', '12', '9', '1', '1', 'truthvalue'],
                ['24', '10', '9', '8448', '1', 'rpm'],
                ['25', '8', '9', '25', '1', 'celsius'],
                ['27', '12', '9', '1', '1', 'truthvalue'],
                ['28', '12', '9', '1', '1', 'truthvalue'],
                ['30', '10', '9', '8448', '1', 'rpm'],
                ['31', '8', '9', '23', '1', 'celsius'],
                ['32', '8', '9', '66', '1', 'celsius'],
                ['33', '8', '9', '37', '1', 'celsius'],
                ['34', '8', '9', '28', '1', 'celsius'],
                ['35', '8', '9', '39', '1', 'celsius'],
            ],
        ],
        {
            'fan': {
                'Sensor Chassis 1': EntitySensor(
                    name='Sensor Chassis 1',
                    reading=4864.0,
                    unit='RPM',
                    state=State.OK,
                    status_descr='OK',
                ),
                'Sensor Chassis 2': EntitySensor(
                    name='Sensor Chassis 2',
                    reading=4864.0,
                    unit='RPM',
                    state=State.OK,
                    status_descr='OK',
                ),
                'Sensor Chassis 3': EntitySensor(
                    name='Sensor Chassis 3',
                    reading=4864.0,
                    unit='RPM',
                    state=State.OK,
                    status_descr='OK',
                ),
                'Sensor Power Supply 0': EntitySensor(
                    name='Sensor Power Supply 0',
                    reading=8448.0,
                    unit='RPM',
                    state=State.OK,
                    status_descr='OK',
                ),
                'Sensor Power Supply 1': EntitySensor(
                    name='Sensor Power Supply 1',
                    reading=8448.0,
                    unit='RPM',
                    state=State.OK,
                    status_descr='OK',
                )
            },
            'power_presence': {
                'Sensor Power Supply 0 Presence': EntitySensor(
                    name='Sensor Power Supply 0 Presence',
                    reading=1.0,
                    unit='boolean',
                    state=State.OK,
                    status_descr='OK',
                ),
                'Sensor Power Supply 0 Input': EntitySensor(
                    name='Sensor Power Supply 0 Input',
                    reading=1.0,
                    unit='boolean',
                    state=State.OK,
                    status_descr='OK',
                ),
                'Sensor Power Supply 1 Presence': EntitySensor(
                    name='Sensor Power Supply 1 Presence',
                    reading=1.0,
                    unit='boolean',
                    state=State.OK,
                    status_descr='OK',
                ),
                'Sensor Power Supply 1 Input': EntitySensor(
                    name='Sensor Power Supply 1 Input',
                    reading=1.0,
                    unit='boolean',
                    state=State.OK,
                    status_descr='OK',
                )
            },
            'temp': {
                'Sensor Power Supply 0': EntitySensor(
                    name='Sensor Power Supply 0',
                    reading=25.0,
                    unit='c',
                    state=State.OK,
                    status_descr='OK',
                ),
                'Sensor Power Supply 1': EntitySensor(
                    name='Sensor Power Supply 1',
                    reading=23.0,
                    unit='c',
                    state=State.OK,
                    status_descr='OK',
                ),
                'Sensor CPU 0/0': EntitySensor(
                    name='Sensor CPU 0/0',
                    reading=66.0,
                    unit='c',
                    state=State.OK,
                    status_descr='OK',
                ),
                'Sensor Chassis Ambient 1': EntitySensor(
                    name='Sensor Chassis Ambient 1',
                    reading=37.0,
                    unit='c',
                    state=State.OK,
                    status_descr='OK',
                ),
                'Sensor Chassis Ambient 2': EntitySensor(
                    name='Sensor Chassis Ambient 2',
                    reading=28.0,
                    unit='c',
                    state=State.OK,
                    status_descr='OK',
                ),
                'Sensor Chassis Ambient 3': EntitySensor(
                    name='Sensor Chassis Ambient 3',
                    reading=39.0,
                    unit='c',
                    state=State.OK,
                    status_descr='OK',
                ),
            },
        },
    ),
])
def test_parse_entity_sensors(string_table, expected_section):
    assert parse_entity_sensors(string_table) == expected_section


@pytest.mark.parametrize('string_table, expected_discovery', [
    (
        [
            [
                ['1', 'PA-500'],
                ['2', 'Fan #1 Operational'],
                ['3', 'Fan #2 Operational'],
                ['4', 'Temperature at MP [U6]'],
                ['5', 'Temperature at DP [U7]'],
            ],
            [
                ['2', '10', '9', '1', '1', 'rpm'],
                ['3', '10', '9', '1', '1', 'rpm'],
                ['4', '8', '9', '37', '1', 'celsius'],
                ['5', '8', '9', '40', '1', 'celsius'],
            ],
        ],
        [
            Service(item='Sensor at MP [U6]'),
            Service(item='Sensor at DP [U7]'),
        ],
    ),
])
def test_discover_entity_sensors_temp(string_table, expected_discovery):
    assert list(discover_entity_sensors_temp(
        parse_entity_sensors(string_table))) == expected_discovery


@pytest.mark.parametrize('string_table, expected_discovery', [
    (
        [
            [
                ['1', 'PA-500'],
                ['2', 'Fan #1 Operational'],
                ['3', 'Fan #2 Operational'],
                ['4', 'Temperature at MP [U6]'],
                ['5', 'Temperature at DP [U7]'],
            ],
            [
                ['2', '10', '9', '1', '1', 'rpm'],
                ['3', '10', '9', '1', '1', 'rpm'],
                ['4', '8', '9', '37', '1', 'celsius'],
                ['5', '8', '9', '40', '1', 'celsius'],
            ],
        ],
        [
            Service(item='Sensor 1 Operational'),
            Service(item='Sensor 2 Operational'),
        ],
    ),
])
def test_discover_entity_sensors_fan(string_table, expected_discovery):
    assert list(discover_entity_sensors_fan(
        parse_entity_sensors(string_table))) == expected_discovery


@pytest.mark.parametrize('string_table, expected_discovery', [
    (
        [
            [
                ['21', 'Power Supply 0 Presence Sensor'],
            ],
            [
                ['21', '12', '9', '1', '1', 'truthvalue'],
            ],
        ],
        [
            Service(item='Sensor Power Supply 0 Presence'),
        ],
    ),
])
def test_discover_entity_sensors_power_presence(string_table, expected_discovery):
    assert list(discover_entity_sensors_power_presence(
        parse_entity_sensors(string_table))) == expected_discovery


@pytest.mark.parametrize('item, params, section, expected_result', [
    (
        'Sensor at DP [U7]',
        {
            'lower': (35.0, 40.0),
        },
        {
            'fan': {
                'Sensor 1 Operational': EntitySensor(
                    name='Sensor 1 Operational',
                    unit='RPM',
                    reading=1.0,
                    status_descr='OK',
                    state=State.OK,
                ),
                'Sensor 2 Operational': EntitySensor(
                    name='Sensor 2 Operational',
                    unit='RPM',
                    reading=1.0,
                    status_descr='OK',
                    state=State.OK,
                ),
            },
            'temp': {
                'Sensor at MP [U6]': EntitySensor(
                    name='Sensor at MP [U6]',
                    unit='c',
                    reading=37.0,
                    status_descr='OK',
                    state=State.OK,
                ),
                'Sensor at DP [U7]': EntitySensor(
                    name='Sensor at DP [U7]',
                    unit='c',
                    reading=40.0,
                    status_descr='OK',
                    state=State.OK,
                ),
            },
        },
        [
            Metric('temp', 40.0),
            Result(state=State.OK, summary='Temperature: 40.0°C'),
            Result(state=State.OK,
                   notice='Configuration: prefer user levels over device levels (no levels found)'),
        ],
    ),
    (
        'Sensor at DP [U7]',
        {},
        {
            'temp': {
                'Sensor at DP [U7]': EntitySensor(
                    name='Sensor at DP [U7]',
                    unit='f',
                    reading=104.0,
                    status_descr='OK',
                    state=State.OK,
                ),
            },
        },
        [
            Metric('temp', 40.0),
            Result(state=State.OK, summary='Temperature: 40.0°C'),
            Result(state=State.OK,
                   notice='Configuration: prefer user levels over device levels (no levels found)'),
        ],
    ),
])
def test_check_entity_sensors_temp(item, params, section, expected_result):
    assert list(check_entity_sensors_temp(item, params, section)) == expected_result


@pytest.mark.parametrize('item, params, section, expected_result', [
    (
        'Sensor 1 Operational',
        {
            'lower': (2000, 1000),
        },
        {
            'fan': {
                'Sensor 1 Operational': EntitySensor(
                    name='Sensor 1 Operational',
                    unit='RPM',
                    reading=1.0,
                    status_descr='OK',
                    state=State.OK,
                ),
                'Sensor 2 Operational': EntitySensor(
                    name='Sensor 2 Operational',
                    unit='RPM',
                    reading=1.0,
                    status_descr='OK',
                    state=State.OK,
                ),
            },
            'temp': {
                'Sensor at MP [U6]': EntitySensor(
                    name='Sensor at MP [U6]',
                    unit='c',
                    reading=37.0,
                    status_descr='OK',
                    state=State.OK,
                ),
                'Sensor at DP [U7]': EntitySensor(
                    name='Sensor at DP [U7]',
                    unit='c',
                    reading=40.0,
                    status_descr='OK',
                    state=State.OK,
                ),
            },
        },
        [
            Result(state=State.OK, summary='Operational status: OK'),
            Result(state=State.CRIT, summary='Speed: 1 RPM (warn/crit below 2000 RPM/1000 RPM)'),
        ],
    ),
])
def test_check_entity_sensors_fan(item, params, section, expected_result):
    assert list(check_entity_sensors_fan(item, params, section)) == expected_result


@pytest.mark.parametrize('item, params, section, expected_result', [
    (
        'Sensor Power Supply 0 Presence',
        {
            'power_off_criticality': 1,
        },
        {
            'power_presence': {
                'Sensor Power Supply 0 Presence': EntitySensor(
                    name='Sensor Power Supply 0 Presence',
                    reading=1.0,
                    unit='boolean',
                    state=State.OK,
                    status_descr='OK',
                ),
            },
        },
        [
            Result(state=State.OK, summary='Powered on'),
        ],
    ),
    (
        'Sensor Power Supply 0 Presence',
        {
            'power_off_criticality': 2,
        },
        {
            'power_presence': {
                'Sensor Power Supply 0 Presence': EntitySensor(
                    name='Sensor Power Supply 0 Presence',
                    reading=0.0,
                    unit='boolean',
                    state=State.OK,
                    status_descr='OK',
                ),
            },
        },
        [
            Result(state=State.CRIT, summary='Powered off'),
        ],
    ),
])
def test_check_entity_sensors_power_presence(item, params, section, expected_result):
    assert list(check_entity_sensors_power_presence(item, params, section)) == expected_result
