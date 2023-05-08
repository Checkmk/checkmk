#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'liebert_fans'


info = [[u'Fan Speed', u'1.3', u'%']]


discovery = {'': [(u'Fan Speed', {})]}


checks = {
    '': [
        (u'Fan Speed', {'levels': (80, 90), 'levels_lower': (2, 1)}, [
            (1, u'1.30 % (warn/crit below 2.00 %/1.00 %)', [
                ('filehandler_perc', 1.3, 80, 90, None, None),
            ]),
        ]),
    ],
}
