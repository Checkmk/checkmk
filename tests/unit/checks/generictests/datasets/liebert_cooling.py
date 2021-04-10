#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'liebert_cooling'


info = [
    [u'Cooling Capacity (Primary)', u'42', u'%'],
    [u'Cooling Capacity (Secondary)', u'42', u'%'],
]


discovery = {
    '': [
        (u'Cooling Capacity (Primary)', {}),
        (u'Cooling Capacity (Secondary)', {}),
    ],
}


checks = {
    '':
    [
        (u'Cooling Capacity (Primary)', {"min_capacity": (45, 40)}, [
            (1, "42.00 % (warn/crit below 45.00 %/40.00 %)", [
                ('capacity_perc', 42.0, None, None),
            ]),
        ]),
        (u'Cooling Capacity (Secondary)', {"max_capacity": (41, 43)}, [
            (1, "42.00 % (warn/crit at 41.00 %/43.00 %)", [
                ('capacity_perc', 42.0, 41.0, 43.0, None, None),
            ]),
        ]),
    ],
}
