#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'liebert_bat_temp'


info = [
    [u'37'],
]



discovery = {
    '': [
        (u'Battery', "liebert_bat_temp_default"),
    ],
}


checks = {
    '': [
        (u'Battery', (30, 40), [
            (1, u'37 \xb0C (warn/crit at 30/40 \xb0C)', [
                ('temp', 37.0, 30.0, 40.0, None, None),
            ]),
        ]),
    ],
}
