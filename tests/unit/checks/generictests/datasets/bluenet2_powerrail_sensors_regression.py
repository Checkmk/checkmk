#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore

checkname = 'bluenet2_powerrail'

info = [
    [['1.1', 'Inlet 1'], ['2.1', 'Inlet'], ['3.1', 'Inlet']],
    [
        ['1.1.1', '\x00\x00\x00\x00\xff\xff\x00\x00'],
        ['1.1.2', '\x00\x00\x00\x01\xff\xff\x00\x00'],
        ['1.1.3', '\x00\x00\x00\x02\xff\xff\x00\x00'],
        ['2.1.1', '\x01\x00\x00\x00\xff\xff\x00\x00'],
        ['2.1.2', '\x01\x00\x00\x01\xff\xff\x00\x00'],
        ['2.1.3', '\x01\x00\x00\x02\xff\xff\x00\x00'],
        ['3.1.1', '\x02\x00\x00\x00\xff\xff\x00\x00'],
        ['3.1.2', '\x02\x00\x00\x01\xff\xff\x00\x00'],
        ['3.1.3', '\x02\x00\x00\x02\xff\xff\x00\x00']
    ], [],
    [
        ['0.1.64.4.255.2.1.0', '256', '2', '-1', '138'],
        ['0.1.64.4.255.2.1.1', '257', '2', '-1', '634'],
        ['0.1.64.4.255.2.1.10', '266', '2', '-1', '70'],
        ['1.1.64.4.1.2.1.0', '256', '2', '-1', '183'],
        ['1.1.64.4.1.2.1.1', '257', '2', '-1', '398'],
        ['1.1.64.4.1.2.1.10', '266', '2', '-1', '44'],
        ['2.1.64.4.1.2.1.0', '256', '2', '-1', '163'],
        ['2.1.64.4.1.2.1.1', '257', '2', '-1', '465'],
        ['2.1.64.4.1.2.1.10', '266', '2', '-1', '48']
    ]
]

discovery = {
    '': [],
    'rcm': [],
    'temp': [
        ('Sensor Master 4/255', {}), ('Sensor PDU 1 4/1', {}),
        ('Sensor PDU 2 4/1', {})
    ],
    'humidity': [
        ('Sensor Master 4/255', 'bluenet2_powerrail_humidity_default_levels'),
        ('Sensor PDU 1 4/1', 'bluenet2_powerrail_humidity_default_levels'),
        ('Sensor PDU 2 4/1', 'bluenet2_powerrail_humidity_default_levels')
    ]
}

checks = {
    'temp': [
        (
            'Sensor Master 4/255', {
                'levels': (30, 35)
            }, [(0, '13.8 \xb0C', [('temp', 13.8, 30, 35, None, None)])]
        ),
        (
            'Sensor PDU 1 4/1', {
                'levels': (30, 35)
            }, [(0, '18.3 \xb0C', [('temp', 18.3, 30, 35, None, None)])]
        ),
        (
            'Sensor PDU 2 4/1', {
                'levels': (30, 35)
            }, [(0, '16.3 \xb0C', [('temp', 16.3, 30, 35, None, None)])]
        )
    ],
    'humidity': [
        (
            'Sensor Master 4/255', (5, 8, 75, 80), [
                (
                    0, '63.40%', [
                        ('humidity', 63.400000000000006, 75, 80, 0, 100)
                    ]
                ), (0, 'OK', [])
            ]
        ),
        (
            'Sensor PDU 1 4/1', (5, 8, 75, 80), [
                (
                    0, '39.80%', [
                        ('humidity', 39.800000000000004, 75, 80, 0, 100)
                    ]
                ), (0, 'OK', [])
            ]
        ),
        (
            'Sensor PDU 2 4/1', (5, 8, 75, 80), [
                (0, '46.50%', [('humidity', 46.5, 75, 80, 0, 100)]),
                (0, 'OK', [])
            ]
        )
    ]
}
