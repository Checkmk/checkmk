#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'liebert_cooling_position'


info = [
    [u'Free Cooling Valve Open Position', u'42', u'%'],
    [u'This is ignored', u'42', u'%'],
]


discovery = {
    '': [
        (u'Free Cooling Valve Open Position', {}),
    ],
}


checks = {
    '': [
        (u'Free Cooling Valve Open Position', {"min_capacity": (50, 45)}, [
            (2, "42.00 % (warn/crit below 50.00 %/45.00 %)", [
                ('capacity_perc', 42.0, None, None, None, None),
            ]),
        ]),
    ],
}
