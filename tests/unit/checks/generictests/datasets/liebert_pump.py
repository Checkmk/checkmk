#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'liebert_pump'


info = [
    [u'Pump Hours', u'3423', u'hr'],
    [u'Pump Hours', u'1', u'hr'],
    [u'Pump Hours Threshold', u'32', u'hr'],
    [u'Pump Hours Threshold', u'32', u'hr'],
]


discovery = {
    '': [
        (u'Pump Hours', {}),
        (u'Pump Hours 2', {}),
    ],
}


checks = {
    '': [
        (u'Pump Hours', {}, [
            (2, u'3423.00 hr (warn/crit at 32.00 hr/32.00 hr)', []),
        ]),
    ],
}
