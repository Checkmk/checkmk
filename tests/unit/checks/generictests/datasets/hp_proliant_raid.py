#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'hp_proliant_raid'

info = [
    ['1', '', '2', '286070', '4294967295'],
    ['2', '', '2', '25753986', '4294967295'],
    ['3', '', '2', '30523320', '4294967295'],
    ['4', '', '2', '15', '4294967295'], ['5', '', '2', '15', '4294967295'],
    ['6', '', '2', '17169273', '4294967295']
]

discovery = {
    '': [
        ('', None), ('2', None), ('3', None), ('4', None), ('5', None),
        ('6', None)
    ]
}

checks = {
    '': [
        ('', {}, [(0, 'Status: OK, Logical volume size: 279.37 GB', [])]),
        ('2', {}, [(0, 'Status: OK, Logical volume size: 24.56 TB', [])]),
        ('3', {}, [(0, 'Status: OK, Logical volume size: 29.11 TB', [])]),
        ('4', {}, [(0, 'Status: OK, Logical volume size: 15.00 MB', [])]),
        ('5', {}, [(0, 'Status: OK, Logical volume size: 15.00 MB', [])]),
        ('6', {}, [(0, 'Status: OK, Logical volume size: 16.37 TB', [])])
    ]
}
