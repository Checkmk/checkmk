#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'printer_input'


info = [
    [u'1.1', u'Printer 1', u'MP Tray', u'9', u'8', u'150', u'0'],
    [u'1.2', u'Custom Printer Name 1', u'Cassette 1', u'4', u'8', u'500', u'400'],
    [u'1.3', u'', u'Cassette 2', u'0', u'8', u'300', u'150'],
    [u'1.4', u'', u'Option Feeder Lower', u'', u'', u'', u''],
    [u'1.5', u'', u'Offline Printer', u'32', u'8', u'10', u'1'],
    [u'1.6', u'', u'Transitioning Printer', u'64', u'8', u'10', u'1'],
]


discovery = {
    '': [
        (u'Printer 1', {}),
        (u'Cassette 2', {}),
        (u'Custom Printer Name 1', {}),
        (u'Offline Printer', {}),
        (u'Transitioning Printer', {}),
    ],
}


checks = {
    '': [
        (u'Printer 1', {'capacity_levels': (0.0, 0.0)}, [
            (0, 'MP Tray', []),
            (1, 'Status: Unavailable and on request', []),
            (1, 'Alerts: Non-Critical', []),
            (0, 'Maximal capacity: 150 sheets', []),
            (0, 'Remaining: 0%', []),
        ]),
        (u'Cassette 2', {'capacity_levels': (0.0, 0.0)}, [
            (0, 'Cassette 2', []),
            (0, 'Status: Available and idle', []),
            (0, 'Alerts: None', []),
            (0, 'Maximal capacity: 300 sheets', []),
            (0, 'Remaining: 50.0%', []),
        ]),
        (u'Custom Printer Name 1', {'capacity_levels': (0.0, 0.0)}, [
            (0, 'Cassette 1', []),
            (0, 'Status: Available and active', []),
            (0, 'Alerts: None', []),
            (0, 'Maximal capacity: 500 sheets', []),
            (0, 'Remaining: 80.0%', []),
        ]),
        (u'Offline Printer', {'capacity_levels': (0.0, 0.0)}, [
            (0, 'Offline Printer', []),
            (2, 'Offline', []),
            (0, 'Status: Available and idle', []),
            (0, 'Alerts: None', []),
            (0, 'Maximal capacity: 10 sheets', []),
            (0, 'Remaining: 10.0%', []),
        ]),
        (u'Transitioning Printer', {'capacity_levels': (0.0, 0.0)}, [
            (0, 'Transitioning Printer', []),
            (0, 'Transitioning', []),
            (0, 'Status: Available and idle', []),
            (0, 'Alerts: None', []),
            (0, 'Maximal capacity: 10 sheets', []),
            (0, 'Remaining: 10.0%', []),
        ]),
    ],
}
