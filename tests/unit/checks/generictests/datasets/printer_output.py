#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'printer_output'


info = [
    [u'1.1', u'Printer 1', u'Output 1', u'0', u'19', u'100', u'15'],
    [u'1.2', u'Printer 2', u'Output 2', u'4', u'19', u'100', u'3'],
    [u'1.2', u'Printer 3', u'Output 3', u'4', u'19', u'100', u'10'],
]


discovery = {
    '': [
        (u'Printer 1', {}),
        (u'Printer 2', {}),
        (u'Printer 3', {}),
    ],
}


checks = {
    '': [
        (u'Printer 1', {'capacity_levels': (5.0, 10.0)}, [
            (0, 'Output 1', []),
            (0, 'Status: Available and idle', []),
            (0, 'Alerts: None', []),
            (0, 'Maximal capacity: 100 percent', []),
            (2, 'Filled: 15.0% (warn/crit at 5.0%/10.0%)', []),
        ]),
        (u'Printer 2', {'capacity_levels': (3.0, 5.0)}, [
            (0, 'Output 2', []),
            (0, 'Status: Available and active', []),
            (0, 'Alerts: None', []),
            (0, 'Maximal capacity: 100 percent', []),
            (1, 'Filled: 3.0% (warn/crit at 3.0%/5.0%)', []),
        ]),
        (u'Printer 3', {'capacity_levels': (40.0, 50.0)}, [
            (0, 'Output 3', []),
            (0, 'Status: Available and active', []),
            (0, 'Alerts: None', []),
            (0, 'Maximal capacity: 100 percent', []),
            (0, 'Filled: 10.0%', []),
        ])
    ],
}
