#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, NamedTuple, Optional
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    State,
)

OIDSysDescr = '.1.3.6.1.2.1.1.1.0'

ENTITY_SENSOR_TYPES = {
    '1': ('other', 'other'),
    '2': ('unknown', 'unknown'),
    '3': ('voltage', 'V'),
    '4': ('voltage', 'V'),
    '5': ('current', 'A'),
    '6': ('power', 'W'),
    '7': ('freqeuncy', 'hz'),
    '8': ('temp', 'c'),
    '9': ('percent', '%'),
    '10': ('fan', 'RPM'),
    '11': ('volume', 'cmm'),  # cubic decimetre dm^3
    '12': ('power_presence', 'boolean'),
}

ENTITY_SENSOR_SCALING = {
    '1': 10 ** (-24),
    '2': 10 ** (-21),
    '3': 10 ** (-18),
    '4': 10 ** (-15),
    '5': 10 ** (-12),
    '6': 10 ** (-9),
    '7': 10 ** (-6),
    '8': 10 ** (-3),
    '9': 1,
    '10': 10 ** (3),
    '11': 10 ** (6),
    '12': 10 ** (9),
    '13': 10 ** (12),
    '14': 10 ** (15),
    '15': 10 ** (18),
    '16': 10 ** (21),
    '17': 10 ** (24),
}


class EntitySensor(NamedTuple):
    name: str
    reading: float
    unit: str
    state: State
    status_descr: str


EntitySensorSection = Dict[str, Dict[str, EntitySensor]]


def sensor_status_descr(status_nr: str) -> str:
    return {
        '1': 'OK',
        '2': 'unavailable',
        '3': 'non-operational',
    }.get(status_nr, status_nr)


def sensor_state(status_nr: str) -> State:
    return {
        '1': State.OK,
        '2': State.CRIT,
        '3': State.WARN,
    }.get(status_nr, State.UNKNOWN)


def reformat_sensor_name(name: str) -> str:
    new_name = name
    for s in ['Fan', 'Temperature', '#', '@', 'Sensor']:
        new_name = new_name.replace(s, '')
    while '  ' in new_name:
        new_name = new_name.replace('  ', ' ')
    return f'Sensor {new_name.strip()}'


def unit_from_device_unit(unit: str) -> Optional[str]:
    '''Converts device units to units known by Check_mk'''
    return {
        'celsius': 'c',
        'fahrenheit': 'f',
        'kelvin': 'k',
    }.get(unit)
