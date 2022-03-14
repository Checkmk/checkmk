#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based.oracle_instance import parse_oracle_instance

checkname = 'oracle_instance'

freeze_time = '2020-01-30 00:00:00'

parsed = parse_oracle_instance([
    [
        'TUX2', '12.1.0.1.0', 'OPEN', 'ALLOWED', 'STARTED', '6735',
        '1297771692', 'ARCHIVELOG', 'PRIMARY', 'NO', 'TUX2'
    ],
    [
        'TUX5', '12.1.0.1.1', 'MOUNTED', 'ALLOWED', 'STARTED', '82883',
        '1297771692', 'NOARCHIVELOG', 'PRIMARY', 'NO', '0', 'TUX5'
    ],
    [
        '+ASM', 'FAILURE',
        'ORA-99999 tnsping failed for +ASM ERROR: ORA-28002: the password will expire within 1 days'
    ]
])

discovery = {
    '': [('+ASM', {}), ('TUX2', {}), ('TUX5', {})],
    'uptime': [('TUX2', {}), ('TUX5', {})]
}

checks = {
    '': [
        (
            '+ASM', {
                'primarynotopen': 2,
                'noforcelogging': 1,
                'logins': 2,
                'noarchivelog': 1
            }, [
                (
                    2,
                    'ORA-99999 tnsping failed for +ASM ERROR: ORA-28002: the password will expire within 1 days',
                    []
                )
            ]
        ),
        (
            'TUX2', {
                'primarynotopen': 2,
                'noforcelogging': 1,
                'logins': 2,
                'noarchivelog': 1
            }, [
                (
                    1,
                    'Database Name TUX2, Status OPEN, Role PRIMARY, Version 12.1.0.1.0, Logins allowed, Log Mode archivelog, Force Logging no(!)',
                    []
                )
            ]
        ),
        (
            'TUX5', {
                'primarynotopen': 2,
                'noforcelogging': 1,
                'logins': 2,
                'noarchivelog': 1
            }, [
                (
                    2,
                    'Database Name 0, Status MOUNTED(!!), Role PRIMARY, Version 12.1.0.1.1, Log Mode noarchivelog(!)',
                    []
                )
            ]
        )
    ],
    'uptime': [
        (
            'TUX2', {"max": (6000, 10000) }, [
                (
                    1, 'Up since 2020-01-29 23:07:45, uptime: 1:52:15 (warn/crit at 1:40:00/2:46:40)', [
                        ('uptime', 6735, 6000, 10000, None, None)
                    ]
                )
            ]
        ),
        (
            'TUX5', {}, [
                (
                    0, 'Up since 2020-01-29 01:58:37, uptime: 23:01:23', [
                        ('uptime', 82883, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
