#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'cisco_temperature'

info = [
    [
        [u'1176', u'Filtered sensor'],
        [u'1177', u'Sensor with large precision'],
        [u'2008', u'Switch 1 - WS-C2960X-24PD-L - Sensor 0'],
        [u'4950', u'Linecard-1 Port-1'],
        [u'21590', u'module-1 Crossbar1(s1)'],
        [u'21591', u'module-1 Crossbar2(s2)'],
        [u'21592', u'module-1 Arb-mux (s3)'],
        [u'31958', u'Transceiver(slot:1-port:1)'],
        [u'300000003', u'Ethernet1/1 Lane 1 Transceiver Voltage Sensor'],
        [u'300000004', u'Ethernet1/1 Lane 1 Transceiver Bias Current Sensor'],
        [u'300000007', u'Ethernet1/1 Lane 1 Transceiver Temperature Sensor'],
        [u'300000013', u'Ethernet1/1 Lane 1 Transceiver Receive Power Sensor'],
        [u'300000014', u'Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor'],
    ],
    [
        [u'1176', u'1', u'9', u'1613258611', u'0', u'1'],
        [u'1177', u'8', u'9', u'1613258611', u'0', u'1'],
        [u'21590', u'8', u'9', u'0', u'62', u'1'],
        [u'21591', u'8', u'9', u'0', u'58', u'1'],
        [u'21592', u'8', u'9', u'0', u'49', u'1'],
        [u'300000003', u'4', u'8', u'0', u'3333', u'1'],
        [u'300000004', u'5', u'7', u'0', u'6002', u'1'],
        [u'300000007', u'8', u'8', u'0', u'24492', u'1'],
        [u'300000013', u'14', u'8', u'0', u'-3271', u'1'],
        [u'300000014', u'14', u'8', u'0', u'1000', u'1'],
    ],
    [
        [u'21590.1', u'115'],
        [u'21590.2', u'125'],
        [u'21591.1', u'115'],
        [u'21591.2', u'125'],
        [u'21592.1', u'115'],
        [u'21592.2', u'125'],
        [u'300000003.1', u'3630'],
        [u'300000003.2', u'3465'],
        [u'300000003.3', u'2970'],
        [u'300000003.4', u'3135'],
        [u'300000004.1', u'10500'],
        [u'300000004.2', u'10500'],
        [u'300000004.3', u'2500'],
        [u'300000004.4', u'2500'],
        [u'300000007.1', u'75000'],
        [u'300000007.2', u'70000'],
        [u'300000007.3', u'-5000'],
        [u'300000007.4', u'0'],
        [u'300000013.1', u'2000'],
        [u'300000013.2', u'-1000'],
        [u'300000013.3', u'-13904'],
        [u'300000013.4', u'-9901'],
        [u'300000014.1', u'1699'],
        [u'300000014.2', u'-1300'],
        [u'300000014.3', u'-11301'],
        [u'300000014.4', u'-7300'],
    ],
    [
        [u'2008', u'SW#1, Sensor#1, GREEN', u'36', u'68', u'1'],
        [u'3008', u'SW#2, Sensor#1, GREEN', u'37', u'68', u'1'],
    ],
    [],
]

discovery = {
    '': [
        (u'Sensor with large precision', {}),
        (u'Ethernet1/1 Lane 1 Transceiver Temperature Sensor', {}),
        (u'SW 1 Sensor 1', {}),
        (u'SW 2 Sensor 1', {}),
        (u'module-1 Arb-mux (s3)', {}),
        (u'module-1 Crossbar1(s1)', {}),
        (u'module-1 Crossbar2(s2)', {}),
    ],
    'dom': [
        (u'Ethernet1/1 Lane 1 Transceiver Receive Power Sensor', {}),
        (u'Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor', {}),
    ]
}

checks = {
    '': [
        (
            u'Sensor with large precision',
            {},
            [(
                0,
                u'0.0 \xb0C',
                [('temp', 0.0, None, None, None, None)],
            )],
        ),
        (
            u'Ethernet1/1 Lane 1 Transceiver Temperature Sensor',
            {},
            [(
                0,
                u'24.5 \xb0C',
                [('temp', 24.492, 70.0, 75.0, None, None)],
            )],
        ),
        (
            u'SW 1 Sensor 1',
            {},
            [(
                0,
                u'36 \xb0C',
                [('temp', 36, 68, 68, None, None)],
            )],
        ),
        (
            u'SW 2 Sensor 1',
            {},
            [(
                0,
                u'37 \xb0C',
                [('temp', 37, 68, 68, None, None)],
            )],
        ),
        (
            u'module-1 Arb-mux (s3)',
            {},
            [(
                0,
                u'49.0 \xb0C',
                [('temp', 49.0, None, None, None, None)],
            )],
        ),
        (u'module-1 Crossbar1(s1)', {}, [
            (0, u'62.0 \xb0C', [('temp', 62.0, None, None, None, None)]),
        ]),
        (
            u'module-1 Crossbar2(s2)',
            {},
            [
                (0, u'58.0 \xb0C', [('temp', 58.0, None, None, None, None)]),
            ],
        ),
    ],
    'dom': [
        (
            u'Ethernet1/1 Lane 1 Transceiver Receive Power Sensor',
            {},
            [(
                0,
                'Status: OK',
                [],
            ),
             (
                 0,
                 'Signal power: -3.27 dBm',
                 [('input_signal_power_dbm', -3.271, -1.0, 2.0, None, None)],
             )],
        ),
        (
            u'Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor',
            {},
            [(
                0,
                'Status: OK',
                [],
            ),
             (
                 1,
                 'Signal power: 1.00 dBm (warn/crit at -1.30 dBm/1.70 dBm)',
                 [('output_signal_power_dbm', 1.0, -1.3, 1.699, None, None)],
             )],
        ),
    ],
}
