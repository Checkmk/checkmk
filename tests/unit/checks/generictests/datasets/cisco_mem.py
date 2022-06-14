#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'cisco_mem'

info = [
    ['Processor', '27086628', '46835412', '29817596'],
    ['I/O', '12409052', '2271012', '2086880'],
    ['Driver text', '40', '1048536', '1048532']
]

discovery = {'': [('I/O', {}), ('Processor', {})]}

checks = {
    '': [
        (
            'I/O', {
                'levels': (80.0, 90.0)
            }, [
                (
                    1,
                    'Usage: 84.53% - 11.8 MiB of 14.0 MiB (warn/crit at 80.00%/90.00% used)',
                    [('mem_used_percent', 84.52995845249721, 80.00000000000001, 90.0, 0.0, None)]
                )
            ]
        ),
        (
            'Processor', {
                'levels': (80.0, 90.0)
            }, [
                (
                    0, 'Usage: 36.64% - 25.8 MiB of 70.5 MiB', [
                        ('mem_used_percent', 36.64215435612978, 80.0, 90.0, 0, None)
                    ]
                )
            ]
        )
    ]
}
