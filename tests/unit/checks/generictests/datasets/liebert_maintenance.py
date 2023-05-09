#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'liebert_maintenance'


info = [[u'Calculated Next Maintenance Month', u'9'],
        [u'Calculated Next Maintenance Year', u'2019']]


freeze_time = "2019-08-23T12:00:00"

discovery = {'': [(None, {})]}


checks = {
    '': [
        (None, {'levels': (10, 5)}, [
            (0, 'Next maintenance: 9/2019', []),
            (1, '7 d (warn/crit below 10 d/5 d)', []),
        ]),
    ],
}
