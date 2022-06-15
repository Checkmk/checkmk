#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'ucd_cpu_util'

freeze_time = '1970-01-01 00:00:01'

info = [
    [
        u'systemStats', u'592290145', u'25568640', u'380156988', u'1565290934',
        u'42658', u'0', u'1929381994', u'1861656198', u'349584702'
    ]
]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {}, [
                (
                    0, 'User: 21.21%', [
                        ('user', 21.210874355159238, None, None, None, None)
                    ]
                ),
                (
                    0, 'System: 25.05%', [
                        ('system', 25.051775056191136, None, None, None, None)
                    ]
                ), (0, 'Wait: <0.01%', [('wait', 0.001464434107289391, None, None, None, None)]),
                (
                    0, 'Total CPU: 46.26%', [
                        ('util', 46.264113845457665, None, None, 0, None)
                    ]
                ),
                (
                    0, '', [
                        ('read_blocks', 1861656198.0, None, None, None, None),
                        ('write_blocks', 1929381994.0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}

mock_item_state = {'': (0, 0)}
