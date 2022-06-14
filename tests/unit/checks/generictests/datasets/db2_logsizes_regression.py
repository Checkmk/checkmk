#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'db2_logsizes'

info = [
    ['[[[db2mpss:ASMPROD]]]'], ['TIMESTAMP', '1474466290'],
    ['usedspace', '2204620'], ['logfilsiz', '2000'], ['logprimary', '5'],
    ['logsecond', '20']
]

discovery = {'': [('db2mpss:ASMPROD', {})]}

checks = {
    '': [
        (
            'db2mpss:ASMPROD', {}, [
                (
                    0, '1.03% used (2.00 of 195 MiB)', [
                        ('fs_used', 2, 156.0, 175.5, 0, 195),
                        ('fs_size', 195, None, None, None, None),
                        (
                            'fs_used_percent', 1.0256410256410255, None, None,
                            None, None
                        )
                    ]
                )
            ]
        )
    ]
}
