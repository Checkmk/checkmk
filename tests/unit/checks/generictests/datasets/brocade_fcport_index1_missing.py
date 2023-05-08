#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'brocade_fcport'

info = [
    [
        [
            u'45', u'6', u'1', u'1', u'2905743640', u'886676077', u'925307562',
            u'12463206', u'3618162349', u'0', u'0', u'0', u'0', u'', u'port44'
        ],
        [
            u'46', u'6', u'1', u'1', u'3419046246', u'972264932',
            u'3137901401', u'544788281', u'569031932', u'0', u'0', u'0', u'82',
            u'', u'port45'
        ],
        [
            u'47', u'6', u'1', u'1', u'1111764110', u'2429196329',
            u'4259150384', u'1651642909', u'569031932', u'0', u'0', u'0', u'6',
            u'', u'port46'
        ],
        [
            u'48', u'6', u'1', u'1', u'1832010527', u'3916222665',
            u'596751007', u'1430959330', u'3618162349', u'0', u'0', u'0', u'0',
            u'', u'port47'
        ]
    ], [[u'45', u'512'], [u'46', u'512'], [u'47', u'512'], [u'48', u'512']],
    [
        [u'805306369', u'6', u'100'], [u'805306370', u'24', u'0'],
        [u'805306371', u'131', u'0'], [u'805306372', u'1', u'0'],
        [u'805306373', u'1', u'0'], [u'805306374', u'1', u'0'],
        [u'805306375', u'1', u'0'], [u'805306376', u'1', u'0'],
        [u'805306377', u'1', u'0'], [u'805306378', u'1', u'0'],
        [u'1073741868', u'56', u'16000'], [u'1073741869', u'56', u'16000'],
        [u'1073741870', u'56', u'16000'], [u'1073741871', u'56', u'16000']
    ], []
]

discovery = {
    '': [
        (
            u'44 ISL port44',
            '{ "phystate": [6], "opstate": [1], "admstate": [1] }'
        ),
        (
            u'45 ISL port45',
            '{ "phystate": [6], "opstate": [1], "admstate": [1] }'
        ),
        (
            u'46 ISL port46',
            '{ "phystate": [6], "opstate": [1], "admstate": [1] }'
        ),
        (
            u'47 ISL port47',
            '{ "phystate": [6], "opstate": [1], "admstate": [1] }'
        )
    ]
}

checks = {
    '': [
        (
            u'44 ISL port44', {
                'assumed_speed': 2.0,
                'phystate': [6],
                'notxcredits': (3.0, 20.0),
                'opstate': [1],
                'c3discards': (3.0, 20.0),
                'admstate': [1],
                'rxencinframes': (3.0, 20.0),
                'rxcrcs': (3.0, 20.0),
                'rxencoutframes': (3.0, 20.0)
            }, [
                (
                    0,
                    'ISL speed: 16 Gbit/s, In: 0.00 B/s, Out: 0.00 B/s, Physical: in sync, Operational: online, Administrative: online',
                    [
                        ('in', 0.0, None, None, 0, 1600000000.0),
                        ('out', 0.0, None, None, 0, 1600000000.0),
                        ('rxframes', 0.0, None, None, None, None),
                        ('txframes', 0.0, None, None, None, None),
                        ('rxcrcs', 0.0, None, None, None, None),
                        ('rxencoutframes', 0.0, None, None, None, None),
                        ('rxencinframes', 0.0, None, None, None, None),
                        ('c3discards', 0.0, None, None, None, None),
                        ('notxcredits', 0.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'45 ISL port45', {
                'assumed_speed': 2.0,
                'phystate': [6],
                'notxcredits': (3.0, 20.0),
                'opstate': [1],
                'c3discards': (3.0, 20.0),
                'admstate': [1],
                'rxencinframes': (3.0, 20.0),
                'rxcrcs': (3.0, 20.0),
                'rxencoutframes': (3.0, 20.0)
            }, [
                (
                    0,
                    'ISL speed: 16 Gbit/s, In: 0.00 B/s, Out: 0.00 B/s, Physical: in sync, Operational: online, Administrative: online',
                    [
                        ('in', 0.0, None, None, 0, 1600000000.0),
                        ('out', 0.0, None, None, 0, 1600000000.0),
                        ('rxframes', 0.0, None, None, None, None),
                        ('txframes', 0.0, None, None, None, None),
                        ('rxcrcs', 0.0, None, None, None, None),
                        ('rxencoutframes', 0.0, None, None, None, None),
                        ('rxencinframes', 0.0, None, None, None, None),
                        ('c3discards', 0.0, None, None, None, None),
                        ('notxcredits', 0.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'46 ISL port46', {
                'assumed_speed': 2.0,
                'phystate': [6],
                'notxcredits': (3.0, 20.0),
                'opstate': [1],
                'c3discards': (3.0, 20.0),
                'admstate': [1],
                'rxencinframes': (3.0, 20.0),
                'rxcrcs': (3.0, 20.0),
                'rxencoutframes': (3.0, 20.0)
            }, [
                (
                    0,
                    'ISL speed: 16 Gbit/s, In: 0.00 B/s, Out: 0.00 B/s, Physical: in sync, Operational: online, Administrative: online',
                    [
                        ('in', 0.0, None, None, 0, 1600000000.0),
                        ('out', 0.0, None, None, 0, 1600000000.0),
                        ('rxframes', 0.0, None, None, None, None),
                        ('txframes', 0.0, None, None, None, None),
                        ('rxcrcs', 0.0, None, None, None, None),
                        ('rxencoutframes', 0.0, None, None, None, None),
                        ('rxencinframes', 0.0, None, None, None, None),
                        ('c3discards', 0.0, None, None, None, None),
                        ('notxcredits', 0.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'47 ISL port47', {
                'assumed_speed': 2.0,
                'phystate': [6],
                'notxcredits': (3.0, 20.0),
                'opstate': [1],
                'c3discards': (3.0, 20.0),
                'admstate': [1],
                'rxencinframes': (3.0, 20.0),
                'rxcrcs': (3.0, 20.0),
                'rxencoutframes': (3.0, 20.0)
            }, [
                (
                    0,
                    'ISL speed: 16 Gbit/s, In: 0.00 B/s, Out: 0.00 B/s, Physical: in sync, Operational: online, Administrative: online',
                    [
                        ('in', 0.0, None, None, 0, 1600000000.0),
                        ('out', 0.0, None, None, 0, 1600000000.0),
                        ('rxframes', 0.0, None, None, None, None),
                        ('txframes', 0.0, None, None, None, None),
                        ('rxcrcs', 0.0, None, None, None, None),
                        ('rxencoutframes', 0.0, None, None, None, None),
                        ('rxencinframes', 0.0, None, None, None, None),
                        ('c3discards', 0.0, None, None, None, None),
                        ('notxcredits', 0.0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
