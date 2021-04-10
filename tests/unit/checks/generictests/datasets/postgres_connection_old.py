#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'postgres_connections'

info = [
    ['[databases_start]'], ['postgres'], ['adwebconnect'], ['[databases_end]'],
    ['current', 'mc', 'datname'], ['1', '100', 'postgres']
]

discovery = {'': [('adwebconnect', {}), ('postgres', {})]}

checks = {
    '': [
        (
            'adwebconnect', {
                'levels_perc': (80.0, 90.0)
            }, [(0, 'No active connections', [('active_connections', 0, 0, 0, 0, 0)]),
               (0, 'No idle connections', [('idle_connections', 0, 0, 0, 0, 0)]) ]
        ),
        (
            'postgres', {
                'levels_perc': (80.0, 90.0)
            }, [(0, 'No active connections', [('active_connections', 0, 0, 0, 0, 0)]),
               (0, 'No idle connections', [('idle_connections', 0, 0, 0, 0, 0)]) ]
        )
    ]
}
