#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'hwg_humidity'

info = [
    ['1', 'Sensor 215', '1', '23.8', '1'],
    ['2', 'Sensor 216', '1', '34.6', '4']
]

discovery = {'': [('2', {})]}

checks = {
    '': [
        (
            '2', (0, 0, 60, 70), [
                (
                    0, '34.60% (Description: Sensor 216, Status: normal)', [
                        ('humidity', 34.6, 60.0, 70.0, 0.0, 100.0)
                    ]
                )
            ]
        )
    ]
}
