#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'liebert_humidity_air'


info = [
    [u'Return Humidity', u'36.5', u'% RH'],
    [u'Cigar Humidity', u'Unavailable', u'% RH'],
]


extra_sections = {
    '': [
        {u'System Model Number': 'Liebert CRV',
         u'System Status': 'Normal Operation',
         u'Unit Operating State': 'standby',
         u'Unit Operating State Reason': 'Reason Unknown'},
    ],
}


discovery = {
    '': [
        (u'Return', {}),
    ],
}


checks = {
    '': [
        (u'Return', {'levels': (50, 55), 'levels_lower': (10, 15)}, [
            (0, u'36.50 % RH', [
                ('humidity', 36.5, 50.0, 55.0, None, None),
            ]),
        ]),
        (u'Cigar', {'levels': (50, 55), 'levels_lower': (10, 15)}, [
            (0, "Unit is in standby (unavailable)", []),
        ]),
    ],
}
