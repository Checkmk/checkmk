#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'hp_proliant_fans'

info = [
    ['1', '3', '3', '2', '2', ''], ['2', '3', '3', '2', '2', ''],
    ['3', '3', '3', '2', '2', ''], ['4', '3', '3', '2', '2', ''],
    ['5', '3', '3', '2', '2', ''], ['6', '3', '3', '2', '2', '']
]

discovery = {
    '': [
        ('1 (system)', None), ('2 (system)', None), ('3 (system)', None),
        ('4 (system)', None), ('5 (system)', None), ('6 (system)', None)
    ]
}

checks = {
    '': [
        (
            '1 (system)', {}, [
                (0, 'FAN Sensor 1 "system", Speed is normal, State is ok', [])
            ]
        ),
        (
            '2 (system)', {}, [
                (0, 'FAN Sensor 2 "system", Speed is normal, State is ok', [])
            ]
        ),
        (
            '3 (system)', {}, [
                (0, 'FAN Sensor 3 "system", Speed is normal, State is ok', [])
            ]
        ),
        (
            '4 (system)', {}, [
                (0, 'FAN Sensor 4 "system", Speed is normal, State is ok', [])
            ]
        ),
        (
            '5 (system)', {}, [
                (0, 'FAN Sensor 5 "system", Speed is normal, State is ok', [])
            ]
        ),
        (
            '6 (system)', {}, [
                (0, 'FAN Sensor 6 "system", Speed is normal, State is ok', [])
            ]
        )
    ]
}
