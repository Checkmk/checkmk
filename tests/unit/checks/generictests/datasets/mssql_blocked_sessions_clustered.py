#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'mssql_blocked_sessions'


info = [
    ['ID 1', 'No blocking sessions'],
    ['ID 1', '1', '232292187', 'Foo', '2'],
]


discovery = {'': [('ID 1', {})]}


checks = {'': [(
    'ID 1',
    {'state': 2},
    [
        (2, 'Summary: 1 blocked by 1 ID(s)', []),
        (0, '\nSession 1 blocked by 2 (Type: Foo, Wait: 2 days 16 hours)', [])
    ]
)]}
