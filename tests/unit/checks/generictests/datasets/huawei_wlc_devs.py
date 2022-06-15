#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'huawei_wlc_devs'

info = [
    ['', '0', '0'], ['', '0', '0'], ['AC6508', '4', '28'], ['', '0', '0'],
    ['', '0', '0'], ['', '0', '0'], ['', '0', '0'], ['', '0', '0'],
    ['', '0', '0'], ['', '0', '0'], ['', '0', '0'], ['', '0', '0'],
    ['', '0', '0'], ['', '0', '0'], ['', '0', '0']
]

discovery = {'': [], 'mem': [('AC6508', {})], 'cpu': [('AC6508', {})]}

checks = {
    'mem': [
        (
            'AC6508', {
                'levels': (80.0, 90.0)
            }, [
                (
                    0, 'Used: 28.00%', [
                        ('mem_used_percent', 28.0, 80.0, 90.0, None, None)
                    ]
                )
            ]
        )
    ],
    'cpu': [
        (
            'AC6508', {
                'levels': (80.0, 90.0)
            }, [
                (
                    0, 'Usage: 4.00%', [
                        ('cpu_percent', 4.0, 80.0, 90.0, None, None)
                    ]
                )
            ]
        )
    ]
}
