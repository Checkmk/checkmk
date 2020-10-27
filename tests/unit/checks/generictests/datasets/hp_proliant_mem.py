#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'hp_proliant_mem'

info = [
    ['0', '0', '4194304', '15', '4', '2', '', '1'],
    ['0', '1', '4194304', '15', '4', '2', '', '1'],
    ['0', '2', '4194304', '15', '4', '2', '', '1'],
    ['0', '3', '0', '15', '2', '1', '', '1'],
    ['0', '4', '4194304', '15', '4', '2', '', '1'],
    ['0', '5', '0', '15', '2', '1', '', '1'],
    ['0', '6', '4194304', '15', '4', '2', '', '2'],
    ['0', '7', '4194304', '15', '4', '2', '', '2'],
    ['0', '8', '4194304', '15', '4', '2', '', '2'],
    ['0', '9', '0', '15', '2', '1', '', '2'],
    ['0', '10', '4194304', '15', '4', '2', '', '2'],
    ['0', '11', '0', '15', '2', '1', '', '2']
]

discovery = {
    '': [
        ('0', None),
        ('1', None),
        ('10', None),
        ('2', None),
        ('4', None),
        ('6', None),
        ('7', None),
        ('8', None)
    ]
}

checks = {
    '': [
        ('0', {}, [
            (0, 'Board: 0', []),
            (0, 'Num: 0', []),
            (0, 'Type: DIMM DDR3', []),
            (0, 'Size: 4.00 GB', []),
            (0, 'Status: good', []),
            (0, 'Condition: ok', []),
        ]),
    ],
}
