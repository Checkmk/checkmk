#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'liebert_chilled_water'


info = [[u'Supply Chilled Water Over Temp',
         u'Inactive Event',
         u'Chilled Water Control Valve Failure',
         u'Inactive Event',
         u'Supply Chilled Water Loss of Flow',
         u'Everything is on fire']]


discovery = {
    '': [
        (u'Supply Chilled Water Over Temp', {}),
        (u'Chilled Water Control Valve Failure', {}),
        (u'Supply Chilled Water Loss of Flow', {}),
    ],
}


checks = {
    '': [
        (u'Supply Chilled Water Over Temp', {}, [
            (0, u'Normal', []),
        ]),
        (u'Supply Chilled Water Loss of Flow', {}, [
            (2, u'Everything is on fire', []),
        ]),
    ],
}
