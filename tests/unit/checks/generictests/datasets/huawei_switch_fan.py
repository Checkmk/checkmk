#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'huawei_switch_fan'

info = [
    [u'1.1', u'50', u'1'],
    [u'1.2', u'80', u'1'],
    [u'2.5', u'50', u'0'],
    [u'2.7', u'90', u'1'],
]

discovery = {
    '': [
        (u'1/1', {}),
        (u'1/2', {}),
        (u'2/2', {}),
    ]
}

checks = {
    '': [
        (
            u'1/1',
            {},
            [(0, '50.00%', [('fan_perc', 50.0, None, None, None, None)])],
        ),
        (
            u'1/2',
            {
                'levels': (70.0, 85.0)
            },
            [(1, '80.00% (warn/crit at 70.00%/85.00%)', [('fan_perc', 80.0, 70.0, 85.0, None, None)])],
        ),
    ]
}
