#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'arista_temp'

info = [
    [
        [
            u'Cpu temp sensor', u'Cpu board temp sensor',
            u'Back-panel temp sensor', u'Front-panel temp sensor'
        ]
    ], [[u'1', u'1', u'1', u'1']], [[u'568', u'470', u'450', u'304']]
]

discovery = {
    '': [
        (u'Back-panel temp sensor', {}), (u'Cpu board temp sensor', {}),
        (u'Cpu temp sensor', {}), (u'Front-panel temp sensor', {})
    ]
}

checks = {
    '': [
        (
            u'Back-panel temp sensor', {}, [
                (0, u'45.0 \xb0C', [('temp', 45.0, None, None, None, None)])
            ]
        ),
        (
            u'Cpu board temp sensor', {}, [
                (0, u'47.0 \xb0C', [('temp', 47.0, None, None, None, None)])
            ]
        ),
        (
            u'Cpu temp sensor', {}, [
                (
                    0, u'56.8 \xb0C', [
                        ('temp', 56.800000000000004, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'Front-panel temp sensor', {}, [
                (
                    0, u'30.4 \xb0C', [
                        ('temp', 30.400000000000002, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
