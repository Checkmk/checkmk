#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'postgres_connections'

info = [
    ['[databases_start]'], ['postgres'], ['app'], ['app_test'],
    ['[databases_end]'], ['datname', 'mc', 'idle', 'active'],
    ['postgres', '100', '4', '9'], ['', '100', '0', '0'],
    ['app', '100', '1', '0'], ['app_test', '100', '2', '0']
]

discovery = {'': [('app', {}), ('app_test', {}), ('postgres', {})]}

checks = {
    '': [
        (
            'app', {
                'levels_perc_active': (80.0, 90.0),
                'levels_perc_idle': (80.0, 90.0),
            }, [
                (
                    0, 'Used active connections: 0', [
                        ('active_connections', 0.0, None, None, 0, 100.0)
                    ]
                ), (0, 'Used active percentage: 0%', []),
                (
                    0, 'Used idle connections: 1', [
                        ('idle_connections', 1.0, None, None, 0, 100.0)
                    ]
                ), (0, 'Used idle percentage: 1.00%', [])
            ]
        ),
        (
            'app_test', {
                'levels_perc_active': (80.0, 90.0),
                'levels_perc_idle': (1.0, 5.0)
            }, [
                (
                    0, 'Used active connections: 0', [
                        ('active_connections', 0.0, None, None, 0, 100.0)
                    ]
                ), (0, 'Used active percentage: 0%', []),
                (
                    0, 'Used idle connections: 2', [
                        ('idle_connections', 2.0, None, None, 0, 100.0)
                    ]
                ), (1, 'Used idle percentage: 2.00% (warn/crit at 1.00%/5.00%)', [])
            ]
        ),
        (
            'postgres', {
                'levels_perc_active': (80.0, 90.0),
                'levels_perc_idle': (80.0, 90.0),
                'levels_abs_active': (2,5)
            }, [
                (
                    2, 'Used active connections: 9 (warn/crit at 2/5)', [
                        ('active_connections', 9.0, 2, 5, 0, 100.0)
                    ]
                ), (0, 'Used active percentage: 9.00%', []),
                (
                    0, 'Used idle connections: 4', [
                        ('idle_connections', 4.0, None, None, 0, 100.0)
                    ]
                ), (0, 'Used idle percentage: 4.00%', [])
            ]
        )
    ]
}
