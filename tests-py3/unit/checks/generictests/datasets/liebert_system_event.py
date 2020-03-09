#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'liebert_system_events'


info = [
    [u'Ambient Air Temperature Sensor Issue', u'Inactive Event'],
    [u'Supply Fluid Over Temp', u'Inactive Event'],
    [u'Supply Fluid Under Temp', u'Inactive Event'],
    [u'Supply Fluid Temp Sensor Issue', u'Active Warning'],
]


discovery = {
    '': [
        (None, {}),
    ],
}


checks = {
    '': [
        (None, {}, [
            (2, u'Supply Fluid Temp Sensor Issue: Active Warning', []),
        ]),
    ],
}
