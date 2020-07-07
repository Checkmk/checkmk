#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'juniper_cpu_util'

info = [
    ['Routing Engine 1', '23'], ['Routing Engine 2', '42'],
    ['TFEB Intake temperature sensor', '7'],
    ['TFEB Intake temperature sensor 2', '0']
]


discovery = {'': [('Routing Engine 1', {}), ('Routing Engine 2', {}), ('TFEB Intake temperature sensor', {})]}

checks = {
    '': [
        (
            'Routing Engine 1', {
                'levels': (80.0, 90.0)
            }, [(0, 'Total CPU: 23.0%', [('util', 23, 80.0, 90.0, 0, 100)])]
        ),
        (
            'Routing Engine 2', {
                'levels': (80.0, 90.0)
            }, [(0, 'Total CPU: 42.0%', [('util', 42, 80.0, 90.0, 0, 100)])]
        )
    ]
}
