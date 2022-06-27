#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'bluenet2_powerrail'

info = [
    [[u'1.1', u'Inlet 1'], [u'2.1', u'Inlet'], [u'3.1', u'Inlet']],
    [
        [u'1.1.1', u'\x00\x00\x00\x00\xff\xff\x00\x00'],
        [u'1.1.2', u'\x00\x00\x00\x01\xff\xff\x00\x00'],
        [u'1.1.3', u'\x00\x00\x00\x02\xff\xff\x00\x00'],
        [u'2.1.1', u'\x01\x00\x00\x00\xff\xff\x00\x00'],
        [u'2.1.2', u'\x01\x00\x00\x01\xff\xff\x00\x00'],
        [u'2.1.3', u'\x01\x00\x00\x02\xff\xff\x00\x00'],
        [u'3.1.1', u'\x02\x00\x00\x00\xff\xff\x00\x00'],
        [u'3.1.2', u'\x02\x00\x00\x01\xff\xff\x00\x00'],
        [u'3.1.3', u'\x02\x00\x00\x02\xff\xff\x00\x00']
    ], [],
    [
        [u'0.1.64.4.255.2.1.0', u'256', u'2', u'-1', u'138'],
        [u'0.1.64.4.255.2.1.1', u'257', u'2', u'-1', u'634'],
        [u'0.1.64.4.255.2.1.10', u'266', u'2', u'-1', u'70'],
        [u'1.1.64.4.1.2.1.0', u'256', u'2', u'-1', u'183'],
        [u'1.1.64.4.1.2.1.1', u'257', u'2', u'-1', u'398'],
        [u'1.1.64.4.1.2.1.10', u'266', u'2', u'-1', u'44'],
        [u'2.1.64.4.1.2.1.0', u'256', u'2', u'-1', u'163'],
        [u'2.1.64.4.1.2.1.1', u'257', u'2', u'-1', u'465'],
        [u'2.1.64.4.1.2.1.10', u'266', u'2', u'-1', u'48']
    ]
]

discovery = {
    '': [],
    'rcm': [],
    'temp': [
        (u'Sensor Master 4/255', {}), (u'Sensor PDU 1 4/1', {}),
        (u'Sensor PDU 2 4/1', {})
    ],
    'humidity': [
        (u'Sensor Master 4/255', 'bluenet2_powerrail_humidity_default_levels'),
        (u'Sensor PDU 1 4/1', 'bluenet2_powerrail_humidity_default_levels'),
        (u'Sensor PDU 2 4/1', 'bluenet2_powerrail_humidity_default_levels')
    ]
}

checks = {
    'temp': [
        (
            u'Sensor Master 4/255', {
                'levels': (30, 35)
            }, [(0, u'13.8 \xb0C', [('temp', 13.8, 30, 35, None, None)])]
        ),
        (
            u'Sensor PDU 1 4/1', {
                'levels': (30, 35)
            }, [(0, u'18.3 \xb0C', [('temp', 18.3, 30, 35, None, None)])]
        ),
        (
            u'Sensor PDU 2 4/1', {
                'levels': (30, 35)
            }, [(0, u'16.3 \xb0C', [('temp', 16.3, 30, 35, None, None)])]
        )
    ],
    'humidity': [
        (
            u'Sensor Master 4/255', (5, 8, 75, 80), [
                (
                    0, '63.40%', [
                        ('humidity', 63.400000000000006, 75, 80, 0, 100)
                    ]
                ), (0, 'OK', [])
            ]
        ),
        (
            u'Sensor PDU 1 4/1', (5, 8, 75, 80), [
                (
                    0, '39.80%', [
                        ('humidity', 39.800000000000004, 75, 80, 0, 100)
                    ]
                ), (0, 'OK', [])
            ]
        ),
        (
            u'Sensor PDU 2 4/1', (5, 8, 75, 80), [
                (0, '46.50%', [('humidity', 46.5, 75, 80, 0, 100)]),
                (0, 'OK', [])
            ]
        )
    ]
}
