#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'qnap_hdd_temp'

info = [
    [u'HDD1', u'37 C/98 F'], [u'HDD2', u'32 C/89 F'], [u'HDD3', u'40 C/104 F'],
    [u'HDD4', u'39 C/102 F'], [u'HDD5', u'45 C/113 F'],
    [u'HDD6', u'43 C/109 F']
]

discovery = {
    '': [
        (u'HDD1', {}), (u'HDD2', {}), (u'HDD3', {}), (u'HDD4', {}),
        (u'HDD5', {}), (u'HDD6', {})
    ]
}

checks = {
    '': [
        (
            u'HDD1', {
                'levels': (40, 45)
            }, [(0, u'37.0 \xb0C', [('temp', 37.0, 40.0, 45.0, None, None)])]
        ),
        (
            u'HDD2', {
                'levels': (40, 45)
            }, [(0, u'32.0 \xb0C', [('temp', 32.0, 40.0, 45.0, None, None)])]
        ),
        (
            u'HDD3', {
                'levels': (40, 45)
            }, [
                (
                    1, u'40.0 \xb0C (warn/crit at 40/45 \xb0C)', [
                        ('temp', 40.0, 40.0, 45.0, None, None)
                    ]
                )
            ]
        ),
        (
            u'HDD4', {
                'levels': (40, 45)
            }, [(0, u'39.0 \xb0C', [('temp', 39.0, 40.0, 45.0, None, None)])]
        ),
        (
            u'HDD5', {
                'levels': (40, 45)
            }, [
                (
                    2, u'45.0 \xb0C (warn/crit at 40/45 \xb0C)', [
                        ('temp', 45.0, 40.0, 45.0, None, None)
                    ]
                )
            ]
        ),
        (
            u'HDD6', {
                'levels': (40, 45)
            }, [
                (
                    1, u'43.0 \xb0C (warn/crit at 40/45 \xb0C)', [
                        ('temp', 43.0, 40.0, 45.0, None, None)
                    ]
                )
            ]
        )
    ]
}
