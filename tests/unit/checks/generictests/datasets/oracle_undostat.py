#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'oracle_undostat'


info = [
    ['TUX2', '160', '3', '1081', '300', '0'],
    ['TUX3', '150', '2', '420', '200', '1'],
]


discovery = {
    '': [
        ('TUX2', {}),
        ('TUX3', {}),
    ],
}


checks = {
    '': [
        ('TUX2', {'levels': (600, 300), 'nospaceerrcnt_state': 2}, [
            (0, 'Undo retention: 18 minutes 1 second', []),
            (0, 'Active undo blocks: 160', []),
            (0, 'Max concurrent transactions: 3', []),
            (0, 'Max querylen: 5 minutes 0 seconds', []),
            (0, 'Space errors: 0', []),
            (0, '', [
                ('activeblk', 160, None, None, None, None),
                ('transconcurrent', 3, None, None, None, None),
                ('tunedretention', 1081, 600, 300, None, None),
                ('querylen', 300, None, None, None, None),
                ('nonspaceerrcount', 0, None, None, None, None),
            ]),
        ]),
        ('TUX3', {'levels': (600, 180), 'nospaceerrcnt_state': 2}, [
            (1, 'Undo retention: 7 minutes 0 seconds (warn/crit below 10 minutes 0 seconds/3 minutes 0 seconds)', []),
            (0, 'Active undo blocks: 150', []),
            (0, 'Max concurrent transactions: 2', []),
            (0, 'Max querylen: 3 minutes 20 seconds', []),
            (2, 'Space errors: 1', []),
            (0, '', [
                ('activeblk', 150, None, None, None, None),
                ('transconcurrent', 2, None, None, None, None),
                ('tunedretention', 420, 600, 180, None, None),
                ('querylen', 200, None, None, None, None),
                ('nonspaceerrcount', 1, None, None, None, None),
            ]),
        ]),
    ],
}
